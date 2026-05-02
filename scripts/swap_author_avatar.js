const fs = require('fs');
const path = require('path');

const ARTICLES_DIR = path.join(__dirname, '..', 'articles');
const files = fs.readdirSync(ARTICLES_DIR).filter(f => f.endsWith('.html'));

const NEW_SIMPLE = `<div class="w-12 h-12 rounded-full overflow-hidden shrink-0 border-2 border-brand-mintDark/40">
          <picture>
            <source srcset="/assets/profile-avatar.webp" type="image/webp" />
            <img src="/assets/profile-avatar.jpg" alt="ぞの" class="w-full h-full object-cover" loading="lazy" />
          </picture>
        </div>`;

const NEW_BIO = `<div class="shrink-0 w-16 h-16 md:w-20 md:h-20 rounded-full overflow-hidden border-2 border-[#c9a96e]/40">
          <picture>
            <source srcset="/assets/profile-avatar.webp" type="image/webp" />
            <img src="/assets/profile-avatar.jpg" alt="ぞの" class="w-full h-full object-cover" loading="lazy" />
          </picture>
        </div>`;

let totalChanged = 0;

for (const f of files) {
  const filepath = path.join(ARTICLES_DIR, f);
  let content = fs.readFileSync(filepath, 'utf-8');
  const original = content;

  // Pattern 1: simple author block (svg with person icon, both single & multi-line)
  // Match the entire div with svg-person inside
  const simplePattern = /<div class="w-12 h-12 rounded-full bg-brand-mintDark\/20 flex items-center justify-center shrink-0">[\s\S]*?<\/svg>\s*<\/div>/g;
  content = content.replace(simplePattern, NEW_SIMPLE);

  // Pattern 2: AUTHOR_BIO_BLOCK_v1 (gold circle with "Z" letter)
  const bioPattern = /<div class="shrink-0 w-16 h-16 md:w-20 md:h-20 rounded-full bg-gradient-to-br from-\[#c9a96e\] to-\[#a8884f\] border-2 border-\[#c9a96e\]\/40 flex items-center justify-center">\s*<span class="text-\[#0d0d0d\] font-serif font-bold text-2xl md:text-3xl">Z<\/span>\s*<\/div>/g;
  content = content.replace(bioPattern, NEW_BIO);

  if (content !== original) {
    fs.writeFileSync(filepath, content, 'utf-8');
    totalChanged++;
    console.log('Updated:', f);
  }
}

console.log('\nTotal updated:', totalChanged);
