"""Рисунок для баннера «Для детей»: двое детей в очках на фоне линзы с коралловым бликом (мотив логотипа).
Рисунок собственный, в цветах логотипа; на сайте он уступает место фотографии images/banner-kids.jpg, если она есть."""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
BLUE, NAVY, CORAL, SKY = '#1D5FD1', '#0F2B5B', '#F0643C', '#9DBBF5'


def kid(tx, ty, s, skin, shade, hair, frame, shirt, trim, girl):
    p = []
    a = p.append
    if girl:
        # два пучка
        a(f'<circle cx="-56" cy="-74" r="29" fill="{hair}"/><circle cx="56" cy="-74" r="29" fill="{hair}"/>')
        a(f'<path d="M-47 -62a13 13 0 0 1 12 -14M65 -76a13 13 0 0 0 -12 -14" fill="none" stroke="{CORAL}" stroke-width="6" stroke-linecap="round"/>')
    # плечи и футболка
    a(f'<path d="M-124 240C-124 150 -92 112 -36 100L36 100C92 112 124 150 124 240Z" fill="{shirt}"/>')
    # шея
    a(f'<path d="M-25 58h50v42a25 21 0 0 1 -50 0Z" fill="{shade}"/>')
    # ворот
    a(f'<path d="M-37 100a37 27 0 0 0 74 0" fill="none" stroke="{trim}" stroke-width="10" stroke-linecap="round"/>')
    # уши
    a(f'<circle cx="-76" cy="10" r="15" fill="{skin}"/><circle cx="76" cy="10" r="15" fill="{skin}"/>')
    a(f'<circle cx="-78" cy="11" r="6.5" fill="{shade}"/><circle cx="78" cy="11" r="6.5" fill="{shade}"/>')
    # голова
    a(f'<path d="M-76 -6C-76 -58 -44 -88 0 -88C44 -88 76 -58 76 -6C76 46 44 84 0 84C-44 84 -76 46 -76 -6Z" fill="{skin}"/>')
    # волосы
    if girl:
        a(f'<path d="M-79 2C-88 -64 -48 -98 0 -98C48 -98 88 -64 79 2C76 -20 70 -34 60 -44C36 -30 -24 -30 -60 -44C-70 -34 -76 -20 -79 2Z" fill="{hair}"/>')
    else:
        a(f'<path d="M-80 4C-92 -64 -52 -101 -2 -101C52 -101 92 -64 80 4C77 -22 68 -40 52 -50C30 -32 -18 -36 -40 -58C-58 -44 -74 -24 -80 4Z" fill="{hair}"/>')
        a(f'<path d="M-14 -97C-8 -117 16 -123 28 -108C16 -110 2 -105 -14 -97Z" fill="{hair}"/>')
    # румянец
    a(f'<circle cx="-47" cy="40" r="14" fill="{CORAL}" opacity=".22"/><circle cx="47" cy="40" r="14" fill="{CORAL}" opacity=".22"/>')
    # стёкла очков
    a('<circle cx="-31" cy="8" r="27" fill="#fff" fill-opacity=".38"/><circle cx="31" cy="8" r="27" fill="#fff" fill-opacity=".38"/>')
    # брови
    a(f'<path d="M-46 -29q14 -9 28 -3M18 -32q14 -6 28 3" fill="none" stroke="{hair}" stroke-width="5" stroke-linecap="round"/>')
    # глаза
    a('<ellipse cx="-31" cy="8" rx="6.5" ry="8.5" fill="#1B2440"/><ellipse cx="31" cy="8" rx="6.5" ry="8.5" fill="#1B2440"/>')
    a('<circle cx="-28.5" cy="5" r="2.4" fill="#fff"/><circle cx="33.5" cy="5" r="2.4" fill="#fff"/>')
    # нос и улыбка
    a(f'<path d="M-5 27q5 6 10 0" fill="none" stroke="{shade}" stroke-width="4" stroke-linecap="round"/>')
    a('<path d="M-19 47q19 19 38 0" fill="none" stroke="#B4503A" stroke-width="5" stroke-linecap="round"/>')
    # очки: дужки, линзы, мост, блики
    a(f'<path d="M-59 4L-80 -2M59 4L80 -2" fill="none" stroke="{frame}" stroke-width="7" stroke-linecap="round"/>')
    a(f'<circle cx="-31" cy="8" r="27" fill="none" stroke="{frame}" stroke-width="8"/><circle cx="31" cy="8" r="27" fill="none" stroke="{frame}" stroke-width="8"/>')
    a(f'<path d="M-5 5q5 -5 10 0" fill="none" stroke="{frame}" stroke-width="7" stroke-linecap="round"/>')
    a('<path d="M-46 -3l9 -9M16 -3l9 -9" fill="none" stroke="#fff" stroke-width="3.5" stroke-linecap="round" opacity=".9"/>')
    return f'<g transform="translate({tx} {ty}) scale({s})">' + ''.join(p) + '</g>'


W, H = 560, 430
svg = (f'<svg class="kids-art" viewBox="0 0 {W} {H}" aria-hidden="true" focusable="false">'
       # линза за детьми и коралловый блик — как буква «a» в логотипе
       f'<circle cx="286" cy="226" r="178" fill="#DCE8FC"/>'
       f'<circle cx="286" cy="226" r="178" fill="none" stroke="{BLUE}" stroke-width="10"/>'
       f'<path d="M146 178A150 150 0 0 1 214 94" fill="none" stroke="{CORAL}" stroke-width="12" stroke-linecap="round"/>'
       + kid(210, 236, 1.0, '#F4CBA6', '#E3AD86', '#4A3122', BLUE, NAVY, SKY, False)
       + kid(396, 270, .86, '#EDBD95', '#D9A27A', '#2B1D17', CORAL, SKY, '#FFFFFF', True)
       + '</svg>')
(ROOT / 'src/kids-art.svg.txt').write_text(svg)
html = ('<!doctype html><meta charset="utf-8"><body style="margin:0;background:linear-gradient(135deg,#E3EEFF,#FFEEE7)">'
        '<div style="width:560px;height:430px;overflow:hidden;background:linear-gradient(115deg,rgba(255,255,255,.92),rgba(255,255,255,.55))">%s</div></body>' % svg)
(ROOT / 'test/kids.html').write_text(html)
print('kids art', len(svg), 'bytes')
