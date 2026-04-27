$ErrorActionPreference = "Stop"

$articlesDir = (Resolve-Path (Join-Path $PSScriptRoot "..\articles")).Path
$thumbsDir = (Resolve-Path (Join-Path $PSScriptRoot "..\assets\thumbnails")).Path
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

# Japanese characters via Unicode code points (script is read as ANSI by PS 5.1 without BOM)
$JP_TOUTEN   = [char]0x3001  # ideographic comma
$JP_KUTEN    = [char]0x3002  # ideographic period
$JP_BAR      = [char]0xFF5C  # fullwidth vertical bar
$JP_NAKAGURO = [char]0x30FB  # katakana middle dot
$JP_OPEN_K   = [char]0x300C  # opening corner bracket
$JP_CLOSE_K  = [char]0x300D  # closing corner bracket
$JP_OPEN_S   = [char]0x3010  # opening black lenticular bracket
$JP_CLOSE_S  = [char]0x3011  # closing black lenticular bracket
$JP_QUESTION = [char]0xFF1F  # fullwidth question
$EM_DASH     = [char]0x2014

$JP_WO = [char]0x3092
$JP_WA = [char]0x306F
$JP_GA = [char]0x304C
$JP_NO = [char]0x306E

# と / に / で は単語の一部になりやすい（とき・タイミング・業種など）ので除外
$breakChars = @($JP_TOUTEN, $JP_KUTEN, $JP_BAR, $JP_NAKAGURO, ' ', ',', $EM_DASH, $JP_OPEN_K, $JP_CLOSE_K, $JP_OPEN_S, $JP_CLOSE_S, $JP_QUESTION)
$particles  = @($JP_WO, $JP_WA, $JP_GA, $JP_NO)

$slugs = @(
    "daigakusei-scout-kachi",
    "joukyou-junbi",
    "iseki-timing",
    "hyakuman-kabe",
    "hosho-ake-kyuritsu",
    "fuuzoku-cabaret-tenkou",
    "chokin-shukan",
    "miken-yarubekikoto",
    "kyujin-site-jouken",
    "area-tokuchou",
    "tsuki-hyakuman",
    "toraburu-taisei",
    "wwork",
    "taiken-nagare",
    "mensetsu-ukaru",
    "scout-mikiburi",
    "noruma-penalty",
    "shimei-3months",
    "kakuteishinkoku",
    "cabaret-vs-lounge",
    "uriage-ageru-mindset",
    "ueno-guide",
    "kabukicho-guide",
    "ikebukuro-guide",
    "shimei-tips",
    "ijyu-checklist",
    "hosho-shikumi",
    "hirusyoku-barenai",
    "kinshicho-guide",
    "saitama-guide"
)

function Escape-Xml($s) {
    $s = $s -replace '&', '&amp;'
    $s = $s -replace '<', '&lt;'
    $s = $s -replace '>', '&gt;'
    $s = $s -replace '"', '&quot;'
    return $s
}

function Split-Title([string]$title) {
    $title = $title.Trim()
    if ($title.Length -le 14) {
        return ,@($title, "")
    }

    [int]$mid = [Math]::Floor($title.Length / 2)
    [int]$bestBreak = -1

    for ($offset = 0; $offset -le 10; $offset++) {
        [int]$posA = $mid + $offset
        [int]$posB = $mid - $offset
        foreach ($pos in @($posA, $posB)) {
            if ($pos -gt 0 -and $pos -lt $title.Length) {
                $ch = $title[$pos]
                if ($breakChars -contains $ch) {
                    $bestBreak = $pos + 1
                    break
                }
            }
        }
        if ($bestBreak -gt 0) { break }
    }

    if ($bestBreak -le 0) {
        for ($offset = 0; $offset -le 8; $offset++) {
            [int]$posA = $mid + $offset
            [int]$posB = $mid - $offset
            foreach ($pos in @($posA, $posB)) {
                if ($pos -gt 0 -and $pos -lt $title.Length) {
                    $ch = $title[$pos]
                    if ($particles -contains $ch) {
                        $bestBreak = $pos + 1
                        break
                    }
                }
            }
            if ($bestBreak -gt 0) { break }
        }
    }

    if ($bestBreak -le 0) { $bestBreak = $mid }

    [string]$line1 = $title.Substring(0, $bestBreak).TrimEnd()
    [string]$line2 = $title.Substring($bestBreak).TrimStart()
    return ,@($line1, $line2)
}

function Get-FontSize($len) {
    if ($len -le 8)  { return 92 }
    if ($len -le 12) { return 76 }
    if ($len -le 16) { return 64 }
    if ($len -le 20) { return 52 }
    return 44
}

$generated = 0
$skipped = 0

foreach ($slug in $slugs) {
    $filePath = Join-Path $articlesDir "$slug.html"
    if (-not (Test-Path -LiteralPath $filePath)) {
        Write-Host "SKIP not found: $slug"
        $skipped++
        continue
    }

    $content = [System.IO.File]::ReadAllText($filePath, $utf8NoBom)

    if ($content -match '(?s)<h1[^>]*>(.*?)</h1>') {
        $h1 = $matches[1]
        $h1 = $h1 -replace '<br[^>]*/?>', ''
        $h1 = $h1 -replace '<[^>]+>', ''
        $h1 = $h1 -replace '&quot;', '"'
        $h1 = $h1 -replace '&amp;', '&'
        $h1 = $h1 -replace '&lt;', '<'
        $h1 = $h1 -replace '&gt;', '>'
        $h1 = $h1 -replace '\s+', ''
        $h1 = $h1.Trim()
    } else {
        Write-Host "WARN no H1: $slug"
        $skipped++
        continue
    }

    $subtitle = ""
    if ($content -match '<meta name="description" content="([^"]+)"') {
        $subtitle = $matches[1]
        if ($subtitle.Length -gt 50) {
            $cutPoint = -1
            for ($i = 30; $i -lt [Math]::Min(60, $subtitle.Length); $i++) {
                if ($subtitle[$i] -eq $JP_KUTEN -or $subtitle[$i] -eq $JP_TOUTEN) {
                    $cutPoint = $i + 1
                    break
                }
            }
            if ($cutPoint -gt 0) {
                $subtitle = $subtitle.Substring(0, $cutPoint)
            } else {
                $subtitle = $subtitle.Substring(0, 50) + ([char]0x2026)  # horizontal ellipsis
            }
        }
    }

    $lines = Split-Title $h1
    $line1 = $lines[0]
    $line2 = $lines[1]

    $maxLen = [Math]::Max($line1.Length, $line2.Length)
    $fontSize = Get-FontSize $maxLen

    if ($line2 -ne "") {
        $line1Y = 290
        $line2Y = $line1Y + $fontSize + 14
    } else {
        $line1Y = 330
        $line2Y = 0
    }

    $line1Esc = Escape-Xml $line1
    $line2Esc = Escape-Xml $line2
    $subtitleEsc = Escape-Xml $subtitle

    $line2Element = ""
    if ($line2 -ne "") {
        $line2Element = "  <text x=`"80`" y=`"$line2Y`" font-family=`"'Noto Sans JP','Hiragino Sans','Yu Gothic Medium','Meiryo',sans-serif`" font-size=`"$fontSize`" font-weight=`"700`" fill=`"#c9a96e`">$line2Esc</text>`r`n"
    }

    $subtitleY = if ($line2 -ne "") { $line2Y + 70 } else { $line1Y + 80 }
    $subtitleElement = ""
    if ($subtitle -ne "") {
        $subtitleElement = "  <text x=`"80`" y=`"$subtitleY`" font-family=`"'Noto Sans JP','Hiragino Sans','Yu Gothic','Meiryo',sans-serif`" font-size=`"22`" fill=`"#9ca3af`" font-weight=`"400`">$subtitleEsc</text>`r`n"
    }

    $eyebrow = "$EM_DASH SCOUT SELECTION"
    $footer  = "GRACE SELECTION $JP_BAR grace-sc.com"

    $svg = @"
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630" width="1200" height="630" preserveAspectRatio="xMidYMid slice">
  <rect width="1200" height="630" fill="#0a0a0a"/>
  <rect x="0" y="0" width="6" height="630" fill="#c9a96e"/>
  <text x="80" y="100" font-family="'Noto Sans JP','Hiragino Sans','Yu Gothic','Meiryo',sans-serif" font-size="20" letter-spacing="6" fill="#c9a96e" font-weight="500">$eyebrow</text>
  <text x="80" y="$line1Y" font-family="'Noto Sans JP','Hiragino Sans','Yu Gothic Medium','Meiryo',sans-serif" font-size="$fontSize" font-weight="700" fill="#ffffff">$line1Esc</text>
$line2Element$subtitleElement  <line x1="80" y1="555" x2="200" y2="555" stroke="#c9a96e" stroke-width="2"/>
  <text x="80" y="595" font-family="'Noto Sans JP','Hiragino Sans','Yu Gothic','Meiryo',sans-serif" font-size="18" fill="#c9a96e" letter-spacing="2" font-weight="500">$footer</text>
</svg>
"@

    $outPath = Join-Path $thumbsDir "$slug.svg"
    [System.IO.File]::WriteAllText($outPath, $svg, $utf8NoBom)
    Write-Host "OK: $slug.svg"
    $generated++
}

Write-Host ""
Write-Host "=== Summary ==="
Write-Host "Generated: $generated"
Write-Host "Skipped: $skipped"
