import re, glob, sys

pat = re.compile(r'\n[ \t]*\n(    <div id="mobile-menu"[\s\S]*?\n    </div>)\n  </header>')

files = [f for f in glob.glob('**/*.html', recursive=True)
         if 'node_modules' not in f.replace('\\', '/')]

apply = '--apply' in sys.argv
ok = 0
changed = 0
skip = []
for f in files:
    s = open(f, encoding='utf-8').read()
    matches = pat.findall(s)
    if len(matches) == 1:
        ok += 1
        if apply:
            new = pat.sub(lambda m: '\n  </header>\n\n' + m.group(1), s, count=1)
            if new != s:
                open(f, 'w', encoding='utf-8', newline='').write(new)
                changed += 1
    else:
        skip.append((f, len(matches)))

print(f'total html         : {len(files)}')
print(f'clean single-match : {ok}')
print(f'non-matching       : {len(skip)}')
if apply:
    print(f'files changed      : {changed}')
for f, n in skip[:30]:
    print(f'  [{n} matches] {f}')
