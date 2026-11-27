// Значки сайта (ICON из src/core4.js) — для каркаса страницы на сервере: build_php.py вставляет их в <span data-icon="…">,
// чтобы кнопки с первой отрисовки были своего размера (скрипт сайта потом ставит те же значки).
const fs = require('fs');
const src = fs.readFileSync(process.argv[2], 'utf8');
const head = src.match(/const ic = d => `[^`]*`;/);
if (!head) throw new Error('no ic');
const start = src.indexOf('const ICON = {');
const end = src.indexOf('\n  };', start);
if (start < 0 || end < 0) throw new Error('no ICON');
const ICON = new Function(head[0] + '\n' + src.slice(start, end + 4) + '\nreturn ICON;')();
process.stdout.write(JSON.stringify(ICON));
