import re, os, glob

RADIAL = '<div class="absolute inset-0 pointer-events-none" style="background:radial-gradient(ellipse 60% 80% at 80% 50%, rgba(201,169,110,0.08) 0%, transparent 70%)"></div>\n    <div class="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-brand-gold/40 to-transparent"></div>\n    '

# ---- STORE DETAIL PAGES ----
store_files = glob.glob('stores/*.html')
store_files = [f for f in store_files if f != 'stores/index.html']

for path in store_files:
    with open(path, encoding='utf-8') as f:
        html = f.read()

    # breadcrumb wrapper
    html = html.replace(
        'class="pt-14 bg-white border-b border-gray-100"',
        'class="pt-14 bg-brand-dark/95"'
    )
    # breadcrumb link hover color already text-gray-400 — make slightly brighter
    html = html.replace(
        'text-xs text-gray-400 flex items-center gap-2"',
        'text-xs text-gray-500 flex items-center gap-2"'
    )

    # hero section class
    html = html.replace(
        'class="bg-white pb-10 px-6 border-b border-gray-100"',
        'class="bg-brand-dark pb-14 px-6 relative overflow-hidden"'
    )

    # inject radial bg after <div class="max-w-4xl mx-auto pt-8">
    html = html.replace(
        '<div class="max-w-4xl mx-auto pt-8">\n      <div class="flex items-start',
        '<div class="max-w-4xl mx-auto pt-8 relative">\n      ' + RADIAL + '<div class="flex items-start'
    )

    # h1 color
    html = html.replace(
        'font-bold text-gray-800 mb-2">',
        'font-bold text-white mb-2">'
    )
    # description text
    html = html.replace(
        'class="text-sm text-gray-500"',
        'class="text-sm text-gray-400"'
    )

    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'updated: {path}')

# ---- ARTICLE DETAIL PAGES ----
article_files = glob.glob('articles/*.html')
article_files = [f for f in article_files if f != 'articles/index.html']

for path in article_files:
    with open(path, encoding='utf-8') as f:
        html = f.read()

    # hero section class
    html = html.replace(
        'class="pt-24 pb-10 px-6 bg-white border-b border-gray-100"',
        'class="pt-24 pb-14 px-6 bg-brand-dark relative overflow-hidden"'
    )

    # inject radial bg after <div class="max-w-2xl mx-auto">
    html = re.sub(
        r'(<div class="max-w-2xl mx-auto">\n)(\s+<div class="flex gap-2 mb-4">)',
        r'\1      ' + RADIAL + r'\2',
        html
    )

    # h1 color
    html = html.replace(
        'font-bold text-gray-800 leading-snug mb-4"',
        'font-bold text-white leading-snug mb-4"'
    )
    # date/meta text keep as-is (text-gray-400 already fine on dark)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'updated: {path}')

print('Done.')
