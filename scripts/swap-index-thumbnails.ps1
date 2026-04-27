$ErrorActionPreference = "Stop"

$articlesDir = (Resolve-Path (Join-Path $PSScriptRoot "..\articles")).Path
$indexPath = Join-Path $articlesDir "index.html"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

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

$content = [System.IO.File]::ReadAllText($indexPath, $utf8NoBom)
$replaced = 0
$missed = 0

foreach ($slug in $slugs) {
    $escSlug = [regex]::Escape($slug)
    # Match the emoji+gradient div block following an <a href> for this slug
    # Pattern: <a href="/articles/SLUG.html" ...> <div class="h-36 bg-gradient-to-br ..."> ... <span class="text-4xl">EMOJI</span> ... </div>
    $pattern = "(?s)(<a href=""/articles/$escSlug\.html""[^>]*data-category=""[^""]*""\s*[^>]*>\s*)<div class=""h-36 bg-gradient-to-br[^""]*flex items-center justify-center""[^>]*>\s*<span class=""text-4xl"">[^<]+</span>\s*</div>"

    $replacement = "`$1<div class=""h-36 overflow-hidden""><img src=""/assets/thumbnails/$slug.svg"" alt="""" class=""w-full h-full object-cover"" loading=""lazy"" /></div>"

    $newContent = [regex]::Replace($content, $pattern, $replacement)
    if ($newContent -ne $content) {
        Write-Host "OK: $slug"
        $content = $newContent
        $replaced++
    } else {
        Write-Host "MISS: $slug"
        $missed++
    }
}

[System.IO.File]::WriteAllText($indexPath, $content, $utf8NoBom)

Write-Host ""
Write-Host "=== Summary ==="
Write-Host "Replaced: $replaced"
Write-Host "Missed: $missed"
