param(
    [Parameter(Mandatory=$true, Position=0)]
    [string[]]$Path
)

function New-TextFromCodePoints([int[]]$Codes) {
    return -join ($Codes | ForEach-Object { [char]$_ })
}

$keyInterviewTime = New-TextFromCodePoints @(0x8bbf,0x8c08,0x65f6,0x95f4)
$keyMeetingTime = New-TextFromCodePoints @(0x4f1a,0x8bae,0x65f6,0x95f4)
$keyInterviewPlace = New-TextFromCodePoints @(0x8bbf,0x8c08,0x5730,0x70b9)
$keyMeetingPlace = New-TextFromCodePoints @(0x4f1a,0x8bae,0x5730,0x70b9)
$keyInterviewers = New-TextFromCodePoints @(0x8bbf,0x8c08,0x4eba,0x5458)
$keyAttendees = New-TextFromCodePoints @(0x53c2,0x4f1a,0x4eba,0x5458)
$keyCompanions = New-TextFromCodePoints @(0x540c,0x884c,0x4eba,0x5458)
$keyInterviewee = New-TextFromCodePoints @(0x88ab,0x8bbf,0x8c08,0x4eba)
$keyTarget = New-TextFromCodePoints @(0x8bbf,0x8c08,0x5bf9,0x8c61)
$fieldKeys = @(
    $keyInterviewTime,
    $keyMeetingTime,
    $keyInterviewPlace,
    $keyMeetingPlace,
    $keyInterviewers,
    $keyAttendees,
    $keyCompanions,
    $keyInterviewee,
    $keyTarget
)

$cnNumbers = New-TextFromCodePoints @(0x4e00,0x4e8c,0x4e09,0x56db,0x4e94,0x516d,0x4e03,0x516b,0x4e5d,0x5341)
$dun = [char]0x3001
$fieldSep = [string]$dun
$leftParen = [char]0xff08
$rightParen = [char]0xff09
$headingPattern = "^[{0}]+{1}|^{2}[{0}]+{3}|^\d+[\.{1}]" -f [Regex]::Escape($cnNumbers), $dun, $leftParen, $rightParen

$files = @()
foreach ($p in $Path) {
    if (Test-Path -LiteralPath $p -PathType Container) {
        $files += Get-ChildItem -LiteralPath $p -File | Where-Object { $_.Extension -in @(".doc", ".docx") }
    } elseif (Test-Path -LiteralPath $p -PathType Leaf) {
        $item = Get-Item -LiteralPath $p
        if ($item.Extension -in @(".doc", ".docx")) {
            $files += $item
        }
    }
}

$files = $files | Sort-Object FullName -Unique
if (-not $files) {
    Write-Error "No .doc or .docx files found."
    exit 1
}

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$results = @()

try {
    foreach ($item in $files) {
        $doc = $null
        try {
            $doc = $word.Documents.Open($item.FullName, $false, $true)
            $text = $doc.Content.Text -replace "`a", " " -replace "`r", "`n"
            $lines = $text -split "`n" | ForEach-Object { ($_.Trim() -replace "\s+", " ") } | Where-Object { $_ }
            $title = ($lines | Select-Object -First 2) -join " / "
            $fields = @()
            foreach ($key in $fieldKeys) {
                if ($lines | Where-Object { $_ -like "$key*" } | Select-Object -First 1) {
                    $fields += $key
                }
            }
            $headings = $lines |
                Where-Object { $_ -match $headingPattern } |
                Select-Object -First 20

            $results += [PSCustomObject]@{
                File = $item.FullName
                Lines = $lines.Count
                Title = $title
                Fields = ($fields -join $fieldSep)
                Headings = ($headings -join " | ")
            }
        } catch {
            $results += [PSCustomObject]@{
                File = $item.FullName
                Lines = 0
                Title = "ERROR"
                Fields = $_.Exception.Message
                Headings = ""
            }
        } finally {
            if ($doc) {
                $doc.Close([ref]$false)
            }
        }
    }
} finally {
    $word.Quit()
}

$results | Format-List
