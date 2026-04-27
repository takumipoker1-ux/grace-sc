$ErrorActionPreference = "Stop"

$articlesDir = (Resolve-Path (Join-Path $PSScriptRoot "..\articles")).Path
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

$dateMap = @{
    "daigakusei-scout-kachi" = "2026-04-24"
    "joukyou-junbi"          = "2026-04-25"
    "iseki-timing"           = "2026-04-25"
    "hyakuman-kabe"          = "2026-04-24"
    "hosho-ake-kyuritsu"     = "2026-04-24"
    "fuuzoku-cabaret-tenkou" = "2026-04-24"
    "chokin-shukan"          = "2026-04-24"
    "miken-yarubekikoto"     = "2026-03-28"
    "kyujin-site-jouken"     = "2026-03-27"
    "area-tokuchou"          = "2026-03-26"
    "tsuki-hyakuman"         = "2026-03-25"
    "toraburu-taisei"        = "2026-03-24"
    "wwork"                  = "2026-03-23"
    "taiken-nagare"          = "2026-04-01"
    "mensetsu-ukaru"         = "2026-04-02"
    "scout-mikiburi"         = "2026-04-03"
    "noruma-penalty"         = "2026-04-04"
    "shimei-3months"         = "2026-04-05"
    "kakuteishinkoku"        = "2026-04-06"
    "cabaret-vs-lounge"      = "2026-04-16"
    "uriage-ageru-mindset"   = "2026-04-16"
    "ueno-guide"             = "2026-04-10"
    "kabukicho-guide"        = "2026-04-11"
    "ikebukuro-guide"        = "2026-04-12"
    "shimei-tips"            = "2026-04-13"
    "ijyu-checklist"         = "2026-04-14"
    "hosho-shikumi"          = "2026-04-15"
    "hirusyoku-barenai"      = "2026-04-22"
    "kinshicho-guide"        = "2026-04-22"
    "saitama-guide"          = "2026-04-22"
    "scout-kangen-kiken"     = "2026-04-23"
    "tsuzukeru-chikara"      = "2026-04-23"
    "seko-mindset"           = "2026-04-23"
    "kurofuku-rikai"         = "2026-04-23"
    "menhera-kouzou"         = "2026-04-23"
    "kyakutanka-jikyu"       = "2026-04-23"
    "area-kyakusou-hikaku"   = "2026-04-23"
    "iwaikin-kangen-wana"    = "2026-04-23"
    "nightwork-3types"       = "2026-04-23"
}

$today = "2026-04-27"
$updated = 0
$skipped = 0

foreach ($slug in $dateMap.Keys) {
    $filePath = Join-Path $articlesDir "$slug.html"
    if (-not (Test-Path -LiteralPath $filePath)) {
        Write-Host "SKIP (not found): $slug.html"
        $skipped++
        continue
    }

    $content = [System.IO.File]::ReadAllText($filePath, $utf8NoBom)

    if ($content -match '"datePublished"') {
        Write-Host "SKIP (already has datePublished): $slug.html"
        $skipped++
        continue
    }

    $publishedDate = $dateMap[$slug]
    $modifiedDate = $today

    $insertion = "`"datePublished`": `"$publishedDate`",`r`n    `"dateModified`": `"$modifiedDate`",`r`n    `"mainEntityOfPage`":"
    $newContent = $content -replace '"mainEntityOfPage":', $insertion

    if ($newContent -eq $content) {
        Write-Host "WARN (no mainEntityOfPage anchor found): $slug.html"
        $skipped++
        continue
    }

    [System.IO.File]::WriteAllText($filePath, $newContent, $utf8NoBom)
    Write-Host "OK: $slug.html (published=$publishedDate, modified=$modifiedDate)"
    $updated++
}

Write-Host ""
Write-Host "=== Summary ==="
Write-Host "Updated: $updated"
Write-Host "Skipped: $skipped"
