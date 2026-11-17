// Достаёт словари интерфейса из исходников: движок (UI) и тема (i18n)
const fs = require('fs');
function literal(src, marker) {
  const start = src.indexOf(marker); if (start < 0) throw new Error('no ' + marker);
  let i = src.indexOf('{', start), depth = 0, q = null;
  for (let j = i; j < src.length; j++) {
    const c = src[j];
    if (q) { if (c === '\\') j++; else if (c === q) q = null; continue; }
    if (c === "'" || c === '"' || c === '`') { q = c; continue; }
    if (c === '/' && src[j + 1] === '/') { j = src.indexOf('\n', j); continue; }
    if (c === '/' && src[j + 1] === '*') { j = src.indexOf('*/', j) + 1; continue; }
    if (c === '{') depth++;
    if (c === '}' && --depth === 0) return src.slice(i, j + 1);
  }
  throw new Error('unbalanced ' + marker);
}
const NB = ' ';
const ui = eval('(' + literal(fs.readFileSync(process.argv[2], 'utf8'), 'const UI = {') + ')');
const th = eval('(' + literal(fs.readFileSync(process.argv[3], 'utf8'), 'const i18n = {') + ')');
const out = {};
for (const src of [ui, th]) for (const l of ['az', 'ru', 'en']) for (const k of Object.keys(src[l] || {})) {
  if (typeof src[l][k] !== 'string') continue;
  (out[k] = out[k] || {})[l] = src[l][k];
}
console.log(JSON.stringify(out));
