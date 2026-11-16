import pathlib
root = pathlib.Path(__file__).parent
src, dist = root / 'src', root / 'dist'
dist.mkdir(exist_ok=True)
read = lambda n: (src / n).read_text(encoding='utf-8').strip()
shared = read('shared.css')
# версии 1–3: русский каталог и прежний движок; версия 4: три языка
targets = {
    'v1': ('optika-1-svetlaya.html', 'data.js', 'core.js'),
    'v2': ('optika-2-yarkaya.html', 'data.js', 'core.js'),
    'v3': ('optika-3-temnaya.html', 'data.js', 'core.js'),
    'v4': ('optika-4-lupa.html', 'data4.js', 'core4.js'),
}
for name, (out, data_f, core_f) in targets.items():
    f = src / f'{name}.html'
    if not f.exists():
        continue
    html = f.read_text(encoding='utf-8')
    for ph in ('/*@@DATA@@*/', '/*@@CORE@@*/', '/*@@SHARED_CSS@@*/'):
        assert ph in html, (name, ph)
    html = html.replace('/*@@DATA@@*/', read(data_f)).replace('/*@@CORE@@*/', read(core_f)).replace('/*@@SHARED_CSS@@*/', shared)
    (dist / out).write_text(html, encoding='utf-8')
    print('built', out, len(html.encode('utf-8')) // 1024, 'KB')
