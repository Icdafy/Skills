# 兼容旧命令；公开库不附带或下载字体。
param([switch]$Check)
$ErrorActionPreference = 'Stop'
$taskFontScript = Join-Path $PSScriptRoot 'ensure_fonts.py'
if ($Check) { & python $taskFontScript --check } else { & python $taskFontScript }
exit $LASTEXITCODE
