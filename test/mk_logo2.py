"""Логотип из исходного файла дизайнера (logo/original/asioptik-logo.svg): готовим его для вставки в страницу.
Берём только фигуры (circle, rect, path); цвета заменяем на переменные, чтобы работал тёмный вариант в подвале."""
import asyncio, base64, pathlib, re, sys
import xml.dom.minidom as minidom
from playwright.async_api import async_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = pathlib.Path(sys.argv[1])
ICO = pathlib.Path(sys.argv[2])
doc = minidom.parseString(SRC.read_text(encoding='utf-8'))
svg = doc.documentElement
BLUE, NAVY, CORAL = '#1D5FD1', '#0F2B5B', '#F0643C'
OK_ATTR = {'circle': ('cx', 'cy', 'r'), 'rect': ('x', 'y', 'width', 'height', 'rx'), 'path': ('d',)}
shapes = []
for el in svg.childNodes:
    if el.nodeType != 1 or el.tagName not in OK_ATTR:
        continue
    a = {k: el.getAttribute(k) for k in OK_ATTR[el.tagName] if el.hasAttribute(k)}
    for v in a.values():
        assert re.fullmatch(r'[0-9A-Za-z .,\-]+', v), v[:40]   # только числа и команды контура
    fill, stroke = el.getAttribute('fill').upper(), el.getAttribute('stroke').upper()
    sw = el.getAttribute('stroke-width')
    assert fill in ('', 'NONE', BLUE, NAVY) and stroke in ('', BLUE, CORAL), (fill, stroke)
    shapes.append({'tag': el.tagName, 'a': a, 'fill': fill, 'stroke': stroke, 'sw': sw, 'cap': el.getAttribute('stroke-linecap')})
print('shapes:', [(s['tag'], s['fill'] or '-', s['stroke'] or '-') for s in shapes])


def draw(s, color_of):
    at = ' '.join(f'{k}="{v}"' for k, v in s['a'].items())
    out = f'<{s["tag"]} {at}'
    if s['stroke']:
        out += f' fill="none" stroke="{color_of(s["stroke"])}" stroke-width="{s["sw"]}"' + (f' stroke-linecap="{s["cap"]}"' if s['cap'] else '')
    else:
        out += f' fill="{color_of(s["fill"])}"'
    return out + '/>'


async def bbox(markup):
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        pg = await b.new_page()
        await pg.set_content(f'<svg xmlns="http://www.w3.org/2000/svg" id="s" viewBox="{svg.getAttribute("viewBox")}" width="800">{markup}</svg>')
        r = await pg.evaluate("""() => { let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
          document.querySelectorAll('#s > *').forEach(el => { const b = el.getBBox(), h = (parseFloat(el.getAttribute('stroke-width')) || 0) / 2;
            x0 = Math.min(x0, b.x - h); y0 = Math.min(y0, b.y - h); x1 = Math.max(x1, b.x + b.width + h); y1 = Math.max(y1, b.y + b.height + h); });
          return [x0, y0, x1, y1]; }""")
        await b.close()
        return r

plain = lambda c: c
all_markup = ''.join(draw(s, plain) for s in shapes)
x0, y0, x1, y1 = asyncio.run(bbox(all_markup))
# буква «a» — кольцо, ножка и блик (фигуры до первого контура буквы)
first_path = next(i for i, s in enumerate(shapes) if s['tag'] == 'path' and not s['stroke'])
a_shapes, letters = shapes[:first_path], shapes[first_path:]
ax0, ay0, ax1, ay1 = asyncio.run(bbox(''.join(draw(s, plain) for s in a_shapes)))
n = lambda v: ('%.1f' % v).rstrip('0').rstrip('.')
vb = f'{n(x0)} {n(y0)} {n(x1 - x0)} {n(y1 - y0)}'
print('tight viewBox:', vb, '| ratio', round((x1 - x0) / (y1 - y0), 3), '| «a»:', n(ax0), n(ay0), n(ax1 - ax0), n(ay1 - ay0))

inline = lambda c: {BLUE: 'currentColor', CORAL: 'var(--coral,#F0643C)'}.get(c, c)
asi = ''.join(draw(s, inline) for s in a_shapes) + ''.join(draw(s, inline) for s in letters if s['fill'] == BLUE)
optik = ''.join(f'<path class="logo-optik" d="{s["a"]["d"]}"/>' for s in letters if s['fill'] == NAVY)
full = f'<svg class="logo-full" viewBox="{vb}" role="img" aria-label="asioptik" focusable="false"><g class="logo-asi">{asi}</g>{optik}</svg>'
mark = f'<svg class="logo-mark" viewBox="{n(ax0)} {n(ay0)} {n(ax1 - ax0)} {n(ay1 - ay0)}" aria-hidden="true" focusable="false">{"".join(draw(s, inline) for s in a_shapes)}</svg>'
# значок вкладки: исходная буква «a» белым на синем квадрате со скруглением
aw, ah = ax1 - ax0, ay1 - ay0
k = 17.6 / ah
white = lambda c: {BLUE: '#fff'}.get(c, c)
fav = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="9" fill="{BLUE}"/>'
       f'<g transform="translate({n(16 - (ax0 + aw / 2) * k)} {n(16 - (ay0 + ah / 2) * k)}) scale({k:.5f})">{"".join(draw(s, white) for s in a_shapes)}</g></svg>')
(ROOT / 'src/logo-full.svg.txt').write_text(full)
(ROOT / 'src/logo-mark.svg.txt').write_text(mark)
(ROOT / 'src/favicon.svg').write_text(fav)
(ROOT / 'src/favicon.ico.b64.txt').write_text(base64.b64encode(ICO.read_bytes()).decode())
print('full', len(full), 'mark', len(mark), 'favicon', len(fav), 'ico b64', len(base64.b64encode(ICO.read_bytes())))
light = full.replace('class="logo-optik"', f'fill="{NAVY}"')
dark = full.replace('class="logo-optik"', 'fill="#9DBBF5"')
W = 676
html = ('<!doctype html><meta charset="utf-8"><body style="margin:0;background:#F2F6FD">'
        f'<div style="padding:20px;width:{W}px;color:{BLUE};line-height:0">{light}</div>'
        f'<div style="padding:20px;display:flex;gap:30px;align-items:center;background:{NAVY};color:#fff"><div style="width:338px;line-height:0">{dark}</div>'
        '<img src="../src/favicon.svg" width="120"><img src="../src/favicon.svg" width="32"><img src="../src/favicon.svg" width="16">'
        f'<div style="color:#fff;width:60px;line-height:0">{mark}</div></div></body>')
(ROOT / 'test/logo.html').write_text(html)
