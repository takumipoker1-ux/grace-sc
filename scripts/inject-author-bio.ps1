$ErrorActionPreference = "Stop"

$articlesDir = (Resolve-Path (Join-Path $PSScriptRoot "..\articles")).Path
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

# Marker comment to detect already-injected bio
$marker = '<!-- AUTHOR_BIO_BLOCK_v1 -->'

# Bio block template (dark theme to contrast with most articles' white body bg)
# Inserted right before <footer ...>
$bioBlock = @'
  <!-- AUTHOR_BIO_BLOCK_v1 -->
  <section class="py-12 px-6 bg-[#0d0d0d] border-y border-white/10">
    <div class="max-w-2xl mx-auto">
      <div class="flex items-start gap-5">
        <div class="shrink-0 w-16 h-16 md:w-20 md:h-20 rounded-full bg-gradient-to-br from-[#c9a96e] to-[#a8884f] border-2 border-[#c9a96e]/40 flex items-center justify-center">
          <span class="text-[#0d0d0d] font-serif font-bold text-2xl md:text-3xl">Z</span>
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-[#c9a96e] text-[10px] font-bold tracking-widest mb-1">&mdash; WRITTEN BY</p>
          <h3 class="text-white font-bold text-base md:text-lg mb-1 leading-tight">ぞの <span class="text-gray-500 font-normal text-xs md:text-sm align-middle">@sc_zono</span></h3>
          <p class="text-gray-400 text-xs md:text-sm leading-relaxed mb-3">
            23歳・現役大学生スカウト / GRACE SELECTION 代表。情報・マーケティングを専攻しながら、独自に300店舗以上を調査。「稼がせるスカウト」を哲学に、未経験〜経験浅い子の同行・面接対策・考え方の共有まで一貫してサポート。4月同行率100%。
          </p>
          <div class="flex flex-wrap gap-x-5 gap-y-2 text-xs">
            <a href="/about.html" class="text-[#c9a96e] hover:text-white font-bold transition-colors whitespace-nowrap">
              ぞののプロフィール詳細 →
            </a>
            <a href="https://www.instagram.com/sc_zono" target="_blank" rel="noopener" class="text-gray-400 hover:text-[#C13584] font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap">
              <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"/></svg>
              Instagramでフォロー
            </a>
          </div>
        </div>
      </div>
    </div>
  </section>

'@

$files = Get-ChildItem -LiteralPath $articlesDir -Filter "*.html" | Where-Object { $_.Name -ne "index.html" }

$injected = 0
$skipped = 0
$noFooter = 0

foreach ($file in $files) {
    $content = [System.IO.File]::ReadAllText($file.FullName, $utf8NoBom)

    if ($content.Contains($marker)) {
        Write-Host "SKIP (already has bio): $($file.Name)"
        $skipped++
        continue
    }

    # Insert before <footer
    $footerPattern = '(<footer\b)'
    $newContent = [regex]::Replace($content, $footerPattern, ($bioBlock + '$1'), 1)

    if ($newContent -eq $content) {
        Write-Host "NO FOOTER: $($file.Name)"
        $noFooter++
        continue
    }

    [System.IO.File]::WriteAllText($file.FullName, $newContent, $utf8NoBom)
    Write-Host "OK: $($file.Name)"
    $injected++
}

Write-Host ""
Write-Host "=== Summary ==="
Write-Host "Injected: $injected"
Write-Host "Skipped:  $skipped"
Write-Host "NoFooter: $noFooter"
