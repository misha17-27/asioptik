"""Логотип asioptik в векторе по картинке заказчика: буквы — Outfit SemiBold, «a» — линза с бликом."""
import math
import pathlib
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen

ROOT = pathlib.Path(__file__).resolve().parent.parent
f = TTFont(str(ROOT / 'test/node_modules/@fontsource/outfit/files/outfit-latin-600-normal.woff2'))
gs = f.getGlyphSet()
cmap = f.getBestCmap()
SC = 0.19246            # пикселей картинки на единицу шрифта
X0, Y0 = 544, 330       # левый верхний угол логотипа на картинке
BASE = 469.1            # базовая линия на картинке
INK_LEFT = [('s', 670), ('i', 758), ('o', 797), ('p', 909), ('t', 1007), ('i', 1085), ('k', 1130)]


def num(v):
    return ('%.1f' % v).rstrip('0').rstrip('.')


def glyph(ch, left):
    g = gs[cmap[ord(ch)]]
    bp = BoundsPen(gs)
    g.draw(bp)
    ox = left - bp.bounds[0] * SC - X0
    pen = SVGPathPen(gs, ntos=num)
    g.draw(TransformPen(pen, (SC, 0, 0, -SC, ox, BASE - Y0)))
    return pen.getCommands()


blue = ''.join(glyph(c, x) for c, x in INK_LEFT[:2])
navy = ''.join(glyph(c, x) for c, x in INK_LEFT[2:])

# буква «a»: кольцо, ножка и коралловый блик
cx, cy = 589.5 - X0, 417.75 - Y0
R_ARC = 21.6


def pt(deg):
    return cx + R_ARC * math.cos(math.radians(deg)), cy - R_ARC * math.sin(math.radians(deg))


(ax, ay), (bx, by) = pt(161), pt(112)
RING = '<circle cx="%s" cy="%s" r="37.4" fill="none" stroke="%%s" stroke-width="15.8"/>' % (num(cx), num(cy))
STEM = '<rect x="%d" y="%d" width="18" height="94" rx="9" fill="%%s"/>' % (635 - X0, 373 - Y0)
ARC = '<path d="M%s %sA%s %s 0 0 1 %s %s" fill="none" stroke="%%s" stroke-width="8.5" stroke-linecap="round"/>' % (num(ax), num(ay), num(R_ARC), num(R_ARC), num(bx), num(by))


def a_mark(color, highlight):
    return RING % color + STEM % color + ARC % highlight


W, H = 1219 - X0 + 1, 507 - Y0 + 1
CORAL = 'var(--coral,#F0643C)'
full = ('<svg class="logo-full" viewBox="0 0 %d %d" role="img" aria-label="asioptik" focusable="false">'
        '<g class="logo-asi">%s<path d="%s" fill="currentColor"/></g><path class="logo-optik" d="%s"/></svg>'
        % (W, H, a_mark('currentColor', CORAL), blue, navy))
# отдельная буква «a» — без полей сверху и снизу, чтобы на узком экране она была крупной
mark = '<svg class="logo-mark" viewBox="0 40 110 100" aria-hidden="true" focusable="false">%s</svg>' % a_mark('currentColor', CORAL)

# значок сайта: синий квадрат со скруглением, белая «a», коралловый блик — как значок на листе с логотипом
K = 0.2
ox, oy = 16 - (cx + 9.75) * K, 16 - (cy + 2.3) * K
fav = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="9" fill="#1D5FD1"/>'
       '<g transform="translate(%s %s) scale(%s)">%s</g></svg>' % (num(ox), num(oy), K, a_mark('#fff', '#F0643C')))

(ROOT / 'src/logo-full.svg.txt').write_text(full)
(ROOT / 'src/logo-mark.svg.txt').write_text(mark)
(ROOT / 'src/favicon.svg').write_text(fav)
print('full', len(full), 'mark', len(mark), 'favicon', len(fav), '| viewBox', W, H)

# проверочная страница: логотип в натуральном размере на фоне листа, тёмный вариант и значок
light = full.replace('class="logo-optik"', 'fill="#0F2B5B"')
dark = full.replace('class="logo-optik"', 'fill="#9DBDF5"')
html = ('<!doctype html><meta charset="utf-8"><body style="margin:0;background:#F2F6FD">'
        '<div style="padding:20px;width:%dpx;color:#1D5FD1;line-height:0">%s</div>'
        '<div style="padding:20px;display:flex;gap:30px;align-items:center;background:#0F2B5B;color:#fff"><div style="width:338px;line-height:0">%s</div>'
        '<img src="../src/favicon.svg" width="120"><img src="../src/favicon.svg" width="32"><img src="../src/favicon.svg" width="16"></div></body>' % (W, light, dark))
(ROOT / 'test/logo.html').write_text(html)
