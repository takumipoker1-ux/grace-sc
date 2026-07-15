const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const ORIGIN = "https://grace-sc.com";

function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    if (entry.name === "node_modules" || entry.name === ".git") return [];
    const absolute = path.join(dir, entry.name);
    return entry.isDirectory() ? walk(absolute) : [absolute];
  });
}

function relativeFile(file) {
  return path.relative(ROOT, file).replace(/\\/g, "/");
}

function publicPath(file) {
  const relative = relativeFile(file);
  if (relative === "index.html") return "/";
  if (relative.endsWith("/index.html")) {
    return `/${relative.slice(0, -"index.html".length)}`;
  }
  return `/${relative}`;
}

function routeToFile(route) {
  let pathname = decodeURI(route.split(/[?#]/, 1)[0]);
  if (pathname === "/") pathname = "/index.html";
  if (pathname.endsWith("/")) pathname += "index.html";
  return pathname.replace(/^\//, "");
}

function extract(html, pattern) {
  const match = html.match(pattern);
  return match ? match[1].trim() : "";
}

const htmlFiles = walk(ROOT).filter((file) => file.endsWith(".html"));
const pages = htmlFiles.map((file) => {
  const html = fs.readFileSync(file, "utf8");
  const relative = relativeFile(file);
  const robots = extract(
    html,
    /<meta\s+[^>]*name=["']robots["'][^>]*content=["']([^"']*)["'][^>]*>/i,
  );
  const canonical = extract(
    html,
    /<link\s+[^>]*rel=["']canonical["'][^>]*href=["']([^"']+)["'][^>]*>/i,
  );
  const h1Count = (html.match(/<h1\b/gi) || []).length;
  const title = extract(html, /<title>([\s\S]*?)<\/title>/i);
  const description = extract(
    html,
    /<meta\s+[^>]*name=["']description["'][^>]*content=["']([^"']*)["'][^>]*>/i,
  );
  const noindex = /\bnoindex\b/i.test(robots);
  const verification = /^google[^/]*\.html$/i.test(relative);

  return {
    file,
    relative,
    html,
    publicPath: publicPath(file),
    canonical,
    h1Count,
    title,
    description,
    indexable: !noindex && !verification,
  };
});

const pageByFile = new Map(pages.map((page) => [page.relative, page]));
const brokenLinks = [];
const incoming = new Map(pages.map((page) => [page.relative, 0]));

for (const page of pages.filter((candidate) => candidate.indexable)) {
  const base = new URL(page.publicPath, ORIGIN);
  const anchorPattern = /<a\b[^>]*href=["']([^"']+)["'][^>]*>/gi;
  let match;
  while ((match = anchorPattern.exec(page.html))) {
    const href = match[1].trim();
    if (!href || href.startsWith("#")) continue;

    let url;
    try {
      url = new URL(href, base);
    } catch {
      brokenLinks.push(`${page.relative} -> ${href} (invalid URL)`);
      continue;
    }

    if (url.origin !== ORIGIN) continue;
    const targetFile = routeToFile(url.pathname);
    const target = pageByFile.get(targetFile);
    if (!target) {
      brokenLinks.push(`${page.relative} -> ${href}`);
      continue;
    }
    incoming.set(target.relative, (incoming.get(target.relative) || 0) + 1);
  }
}

const canonicalProblems = pages
  .filter((page) => page.indexable)
  .flatMap((page) => {
    const expected = new URL(page.publicPath, ORIGIN).href;
    if (!page.canonical) return [`${page.relative}: canonical missing`];
    if (page.canonical !== expected) {
      return [`${page.relative}: ${page.canonical} (expected ${expected})`];
    }
    return [];
  });

const metadataProblems = pages
  .filter((page) => page.indexable)
  .flatMap((page) => {
    const problems = [];
    if (!page.title) problems.push(`${page.relative}: title missing`);
    if (!page.description) problems.push(`${page.relative}: description missing`);
    if (page.h1Count !== 1) {
      problems.push(`${page.relative}: h1 count is ${page.h1Count}`);
    }
    return problems;
  });

const jsonLdProblems = [];
for (const page of pages) {
  const jsonLdPattern = /<script\b[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi;
  let match;
  let index = 0;
  while ((match = jsonLdPattern.exec(page.html))) {
    index += 1;
    try {
      JSON.parse(match[1]);
    } catch (error) {
      jsonLdProblems.push(`${page.relative} block ${index}: ${error.message}`);
    }
  }
}

const orphans = pages
  .filter(
    (page) =>
      page.indexable &&
      page.publicPath !== "/" &&
      (incoming.get(page.relative) || 0) === 0,
  )
  .map((page) => page.relative);

const sitemap = fs.readFileSync(path.join(ROOT, "sitemap.xml"), "utf8");
const sitemapUrls = new Set(
  [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((match) => match[1].trim()),
);
const indexableUrls = new Set(
  pages
    .filter((page) => page.indexable)
    .map((page) => new URL(page.publicPath, ORIGIN).href),
);
const missingFromSitemap = [...indexableUrls].filter((url) => !sitemapUrls.has(url));
const extraInSitemap = [...sitemapUrls].filter((url) => !indexableUrls.has(url));
const lastmodCount = (sitemap.match(/<lastmod>\d{4}-\d{2}-\d{2}<\/lastmod>/g) || [])
  .length;

const result = {
  htmlPages: pages.length,
  indexablePages: indexableUrls.size,
  sitemapUrls: sitemapUrls.size,
  sitemapLastmods: lastmodCount,
  brokenLinks,
  orphanIndexablePages: orphans,
  canonicalProblems,
  metadataProblems,
  jsonLdProblems,
  missingFromSitemap,
  extraInSitemap,
};

console.log(JSON.stringify(result, null, 2));

const hasProblems = [
  brokenLinks,
  orphans,
  canonicalProblems,
  metadataProblems,
  jsonLdProblems,
  missingFromSitemap,
  extraInSitemap,
].some((problems) => problems.length > 0);

if (lastmodCount !== sitemapUrls.size || hasProblems) process.exitCode = 1;
