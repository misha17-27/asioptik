"""Шрифты сайта на PHP лежат на самом сайте (site/assets/fonts/), а не берутся у Google Fonts.

Так браузеру не нужно соединяться ещё с двумя чужими серверами, а главные шрифты страница просит заранее
(<link rel="preload"> в каркасе страницы): текст сразу появляется своим шрифтом и потом не сдвигается.
Версия сайта одним файлом (dist/) по-прежнему берёт шрифты у Google Fonts.

Источник — пакеты @fontsource (те же шрифты, что у Google Fonts): они ставятся в test/ командой npm install.
Скрипт запускают, только когда меняется набор шрифтов; готовые файлы хранятся в репозитории.
  python3 build_fonts.py
Пишет: site/assets/fonts/*.woff2, лицензии шрифтов (*-OFL.txt) и src/fonts4.css — правила @font-face,
которые build_php.py ставит в начало assets/css/app.css.

Для каждого начертания три файла, браузер скачивает только нужные странице:
  latin    — латиница, цифры, знаки препинания (как у Google Fonts);
  cyrillic — русские буквы (как у Google Fonts);
  az       — буквы азербайджанского алфавита сверх латиницы (Ə ə Ğ ğ İ ı Ş ş) и знак манат ₼. У Google Fonts это часть
             большого набора latin-ext (у Noto Serif Display около 60 КБ на начертание), здесь — только нужные знаки.
"""
import pathlib
import re
import shutil

from fontTools import subset

ROOT = pathlib.Path(__file__).resolve().parent
FS = ROOT / 'test' / 'node_modules' / '@fontsource'
OUT = ROOT / 'site' / 'assets' / 'fonts'
CSS = ROOT / 'src' / 'fonts4.css'

# семейство в CSS, пакет и начертания — те же, что сайт одним файлом берёт у Google Fonts
FAMILIES = [
    ('Noto Serif Display', 'noto-serif-display', [300, 400]),
    ('Onest', 'onest', [500, 700]),
    ('Ysabeau Office', 'ysabeau-office', [400, 500, 600, 700]),
]
AZ_RANGE = 'U+0100-017F,U+018F,U+0259,U+20A0-20C0'


def unicodes(rng):
    out = set()
    for part in rng.split(','):
        a, _, b = part.strip()[2:].partition('-')
        out.update(range(int(a, 16), int(b or a, 16) + 1))
    return out


def range_of(pkg, subset_name, weight):
    """unicode-range набора из CSS пакета — тот же, что у Google Fonts."""
    css = (FS / pkg / f'{weight}.css').read_text(encoding='utf-8')
    m = re.search(r'/\* %s-%s-%d-normal \*/\s*@font-face \{[^}]*unicode-range: ([^;]+);' % (pkg, subset_name, weight), css)
    assert m, (pkg, subset_name, weight)
    return m.group(1).strip()


def az_subset(src, dst):
    opts = subset.Options()
    opts.flavor = 'woff2'
    opts.layout_features = ['*']   # кернинг и лигатуры остаются
    opts.name_IDs = ['*']          # в файле остаются название шрифта и его лицензия
    opts.name_languages = ['*']
    font = subset.load_font(str(src), opts)
    sub = subset.Subsetter(opts)
    sub.populate(unicodes=unicodes(AZ_RANGE))
    sub.subset(font)
    subset.save_font(font, str(dst), opts)


def main():
    if OUT.exists():
        for f in OUT.glob('*.woff2'):
            f.unlink()
    OUT.mkdir(parents=True, exist_ok=True)
    rules = ['/* Шрифты сайта (файлы в assets/fonts, их собирает build_fonts.py). Наборы знаков — как у Google Fonts:',
             '   браузер скачивает только те файлы, знаки из которых есть на странице. Набор latin стоит последним:',
             '   знак, который есть в двух наборах, браузер берёт из него (правила проверяются с конца). */']
    total = 0
    for family, pkg, weights in FAMILIES:
        files = FS / pkg / 'files'
        for w in weights:
            for name, rng in (('cyrillic', range_of(pkg, 'cyrillic', w)), ('az', AZ_RANGE), ('latin', range_of(pkg, 'latin', w))):
                dst = OUT / f'{pkg}-{name}-{w}.woff2'
                if name == 'az':
                    az_subset(files / f'{pkg}-latin-ext-{w}-normal.woff2', dst)
                else:
                    shutil.copy(files / f'{pkg}-{name}-{w}-normal.woff2', dst)
                total += dst.stat().st_size
                rules.append("@font-face{font-family:'%s';font-style:normal;font-weight:%d;font-display:swap;"
                             "src:url(../fonts/%s) format('woff2');unicode-range:%s}" % (family, w, dst.name, rng))
        shutil.copy(FS / pkg / 'LICENSE', OUT / f'{pkg}-OFL.txt')
    CSS.write_text('\n'.join(rules) + '\n', encoding='utf-8')
    print('site/assets/fonts: %d файлов, %d КБ' % (len(list(OUT.glob('*.woff2'))), total // 1024))


if __name__ == '__main__':
    main()
