"""Сборка сайта на PHP: дописывает в папку site/ файлы, которые получаются из исходников страницы (src/).

PHP-файлы сайта и админ-панели лежат прямо в site/ и правятся там. Этот скрипт собирает страницу
(build.py) и раскладывает её по файлам, которые сервер отдаёт посетителю:
  site/app/site/shell.html — каркас страницы, в который сервер подставляет заголовки и данные из базы
  site/assets/css/app.css  — оформление сайта
  site/assets/js/app.js    — работа сайта (корзина, страницы, формы)
  site/app/data/seed.json  — первые данные: товары, разделы, бренды, статьи, услуги, настройки
  site/favicon.ico         — значок сайта из папки logo/
Подключение к базе, загруженные фото, кэш и журналы (storage/, uploads/) скрипт не трогает.
"""
import json
import pathlib
import re
import shutil
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / 'site'

subprocess.run(['python3', str(ROOT / 'build.py')], check=True, capture_output=True)
html = (ROOT / 'dist' / 'optika-4-lupa.html').read_text(encoding='utf-8')

# ---------- части собранной страницы ----------
scripts = list(re.finditer(r'<script>\n(.*?)\n</script>', html, flags=re.S))
styles = list(re.finditer(r'<style>\n(.*?)\n</style>', html, flags=re.S))
assert len(scripts) == 3 and len(styles) == 1, (len(scripts), len(styles))
data_js, theme_js, core_js = (m.group(1) for m in scripts)
css = styles[0].group(1)

shell = html
shell = shell.replace(scripts[2].group(0), '')
shell = shell.replace(scripts[1].group(0), '<script src="%%BASE%%assets/js/app.js?v=%%VER%%"></script>')
shell = shell.replace(styles[0].group(0), '<link rel="stylesheet" href="%%BASE%%assets/css/app.css?v=%%VER%%">')
shell = shell.replace(scripts[0].group(0), '<script>\n%%DATA%%</script>')


def sub1(pattern, repl, text, flags=0):
    new, n = re.subn(pattern, repl, text, count=1, flags=flags)
    assert n == 1, pattern
    return new


shell = sub1(r'<html lang="az">', '<html lang="%%LANG%%">', shell)
shell = sub1(r'<title>[^<]*</title>', '<title>%%TITLE%%</title>', shell)
shell = sub1(r'<meta name="description" content="[^"]*">', '<meta name="description" content="%%DESC%%">', shell)
shell = sub1(r'<link rel="canonical" href="[^"]*">\n', '<link rel="canonical" href="%%CANON%%">\n%%ROBOTS%%', shell)
shell, n = re.subn(r'<link rel="alternate" hreflang="[a-z]+" href="[^"]*">\n', '', shell)
assert n == 3
shell = sub1(r'<meta property="og:type" content="website">\n', '%%HREFLANG%%<meta property="og:type" content="website">\n', shell)
shell = sub1(r'<meta property="og:site_name" content="[^"]*">', '<meta property="og:site_name" content="%%SHOP%%">', shell)
shell = sub1(r'<meta property="og:url" content="[^"]*">', '<meta property="og:url" content="%%CANON%%">', shell)
shell = sub1(r'<meta property="og:title" content="[^"]*">', '<meta property="og:title" content="%%TITLE%%">', shell)
shell = sub1(r'<meta property="og:description" content="[^"]*">', '<meta property="og:description" content="%%DESC%%">', shell)
# ссылки меню: на сервере адреса обычные (/catalog), а не ?page=catalog
shell, n = re.subn(r'href="\?page=([a-z]+)"', r'href="%%BASE%%\1"', shell)
assert n >= 8, n
# то же для страниц «для кого»: ?page=catalog&aud=kids → /catalog?aud=kids
shell, n = re.subn(r'href="\?page=([a-z]+)&amp;([a-z]+=[a-z0-9-]+)"', r'href="%%BASE%%\1?\2"', shell)
assert n == 2, n
assert 'href="?page=' not in shell
shell = shell.replace('Адреса: ?page=catalog, ?page=about, ?page=blog, ?page=contacts', 'Адреса: /catalog, /about, /blog, /contacts')

# ---------- первые данные из настроек сайта ----------
node = subprocess.run(['node', '-e', '''
const fs = require('fs');
const src = fs.readFileSync(process.argv[1], 'utf8');
const d = new Function(src + ';return {CONFIG,CATEGORIES,RX,AUDIENCES,PRODUCTS,BRANDS,SERVICES,ABOUT,POSTS};')();
process.stdout.write(JSON.stringify(d));
''', str(ROOT / 'src' / 'data4.js')], check=True, capture_output=True, text=True)
d = json.loads(node.stdout)


def drop_placeholder_images(nodeval):
    """Места под фото из папки images не переносим: на сервере фото загружаются через админ-панель."""
    if isinstance(nodeval, dict):
        if isinstance(nodeval.get('img'), str) and nodeval['img'].startswith('images/'):
            del nodeval['img']
        for v in nodeval.values():
            drop_placeholder_images(v)
    elif isinstance(nodeval, list):
        for v in nodeval:
            drop_placeholder_images(v)


for key in ('CATEGORIES', 'AUDIENCES', 'ABOUT'):
    drop_placeholder_images(d[key])

home = set()
for a in d['AUDIENCES']:
    for nodeval in [a] + a.get('parts', []):
        home.update(nodeval.get('pick', []))

STRUCT = ['art', 'shape', 'metal', 'sw', 'sun', 'grad', 'tone', 'pack', 'opts', 'kind', 'rx', 'colorLabel', 'add', 'withLenses']
templates = {}
products = []
for p in d['PRODUCTS']:
    data = {k: v for k, v in p.items() if k != 'id'}
    if p['id'] in home:
        data['home'] = True
    products.append({'slug': p['id'], 'data': data})
    templates.setdefault(p['cat'], {k: p[k] for k in STRUCT if k in p})


def rows(items):
    return [{'slug': x['id'], 'data': {k: v for k, v in x.items() if k != 'id'}} for x in items]


config = dict(d['CONFIG'])
seed = {
    'settings': {'config': config, 'rx': d['RX'], 'about': d['ABOUT'], 'audiences': d['AUDIENCES'], 'templates': templates},
    'items': {'category': rows(d['CATEGORIES']), 'brand': rows(d['BRANDS']), 'product': products, 'service': rows(d['SERVICES']), 'post': rows(d['POSTS'])},
}

# ---------- записываем собранные файлы в папку сайта ----------
def put(rel, text):
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')


put('app/site/shell.html', shell)
put('app/data/seed.json', json.dumps(seed, ensure_ascii=False, separators=(',', ':')))
put('assets/css/app.css', css + '\n')
put('assets/js/app.js', theme_js + '\n' + core_js + '\n')
# все надписи сайта на трёх языках — чтобы их можно было менять в админ-панели, раздел «Страницы»
texts = subprocess.run(['node', str(ROOT / 'build_texts.js'), str(ROOT / 'src' / 'core4.js'), str(ROOT / 'src' / 'v4.html')], capture_output=True, text=True, check=True).stdout
assert len(json.loads(texts)) > 200
put('app/data/texts.json', texts.strip())
for folder in ('storage/cache', 'storage/logs', 'uploads'):   # пустые папки, которые должны быть на хостинге
    (OUT / folder).mkdir(parents=True, exist_ok=True)
    if not (OUT / folder / '.gitkeep').exists():
        (OUT / folder / '.gitkeep').write_text('')
shutil.copy(ROOT / 'logo' / 'favicon.ico', OUT / 'favicon.ico')
cache = OUT / 'storage' / 'cache' / 'site.json'
if cache.exists():
    try:
        cache.unlink()   # данные для страницы соберутся заново при первом открытии
    except OSError:
        pass

print('site/: shell %d KB, app.js %d KB, app.css %d KB, seed %d KB | products %d' % (
    len(shell) // 1024, len(theme_js + core_js) // 1024, len(css) // 1024, (OUT / 'app' / 'data' / 'seed.json').stat().st_size // 1024, len(products)))
