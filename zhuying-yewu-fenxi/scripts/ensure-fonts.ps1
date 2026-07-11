# ensure-fonts.ps1 — 公文字体自动检测与安装（无需管理员权限，用户级安装）
# 用法: powershell -ExecutionPolicy Bypass -File ensure-fonts.ps1
# 逻辑: 逐个检测字体是否已安装(HKLM/HKCU注册表) -> 未安装则从技能 assets/fonts 复制安装
#       -> assets 缺失时通过 gh api 从 GitHub 仓库(Icdafy/Skills)下载后安装

$ErrorActionPreference = 'Stop'

$fonts = @(
    @{ Family = '仿宋_GB2312';    AltFamily = 'FangSong_GB2312';    File = 'simfang.ttf' },
    @{ Family = '楷体_GB2312';    AltFamily = 'KaiTi_GB2312';       File = 'KaiTi_GB2312.ttf' },
    @{ Family = '方正小标宋简体'; AltFamily = 'FZXiaoBiaoSong-B05S'; File = 'FZXiaoBiaoSongJT.ttf' }
)

$assetsDir   = Join-Path (Split-Path $PSScriptRoot -Parent) 'assets\fonts'
$userFontDir = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Fonts'
$hklmKey     = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts'
$hkcuKey     = 'HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Fonts'
$repoPath    = 'repos/Icdafy/Skills/contents/zhuying-yewu-fenxi/assets/fonts'

function Test-FontInstalled($family, $altFamily) {
    foreach ($key in @($hklmKey, $hkcuKey)) {
        if (Test-Path $key) {
            $props = (Get-ItemProperty $key).PSObject.Properties.Name
            foreach ($p in $props) {
                if ($p -like "$family*" -or $p -like "$altFamily*") { return $true }
            }
        }
    }
    return $false
}

function Install-UserFont($family, $file) {
    $srcFile = Join-Path $assetsDir $file
    if (-not (Test-Path $srcFile)) {
        Write-Output "  assets 中未找到 $file，尝试从 GitHub 下载..."
        if (-not (Test-Path $assetsDir)) { New-Item -ItemType Directory -Force $assetsDir | Out-Null }
        # 注意：不能用 gh api > 文件（PowerShell 重定向按文本转码，二进制会损坏），
        # 用 gh 取 token 后经 Invoke-WebRequest -OutFile 原始字节落盘
        if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw "未安装 gh CLI，无法从 GitHub 下载 $file" }
        $tok = (& gh auth token 2>$null)
        if (-not $tok) { throw "gh 未登录（运行 gh auth login），无法从 GitHub 下载 $file" }
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri "https://api.github.com/$repoPath/$file" `
            -Headers @{ Authorization = "token $tok"; Accept = 'application/vnd.github.raw' } `
            -OutFile $srcFile -UseBasicParsing
        if ((Get-Item $srcFile).Length -lt 100000) { throw "下载 $file 失败（文件过小），请检查网络与 gh 登录状态" }
    }
    if (-not (Test-Path $userFontDir)) { New-Item -ItemType Directory -Force $userFontDir | Out-Null }
    $dest = Join-Path $userFontDir $file
    Copy-Item $srcFile $dest -Force
    if (-not (Test-Path $hkcuKey)) { New-Item -Path $hkcuKey -Force | Out-Null }
    New-ItemProperty -Path $hkcuKey -Name "$family (TrueType)" -Value $dest -PropertyType String -Force | Out-Null
    Write-Output "  已安装(用户级): $family -> $dest"
}

$missing = 0
foreach ($f in $fonts) {
    if (Test-FontInstalled $f.Family $f.AltFamily) {
        Write-Output "[OK] $($f.Family) 已安装，直接使用"
    } else {
        Write-Output "[缺失] $($f.Family) 未安装，开始安装..."
        Install-UserFont $f.Family $f.File
        $missing++
    }
}

if ($missing -gt 0) {
    Write-Output "共安装 $missing 个字体。已打开的 Word 需重启后生效。"
} else {
    Write-Output "全部公文字体已就绪。"
}
