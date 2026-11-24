"""Админ-панель: вход, обзор, заказы, клиенты, страницы и надписи, товары, бренды, статьи, настройки, загрузка фото и защита."""
import asyncio, pathlib, re, subprocess, urllib.request
from playwright.async_api import async_playwright
from run import ROOT
B = 'http://127.0.0.1:8771'
SH = f'{ROOT}/shots'
PW = 'Test-Admin-2026'
def sql(q):
    return subprocess.run(['mariadb', '--socket=/tmp/mysql-run/mysqld.sock', '-uroot', 'asioptik_test', '-N', '-e', q], capture_output=True, text=True).stdout.strip()
def raw(path):
    """Страница в том виде, в каком её отдаёт сервер и видит поисковик."""
    return urllib.request.urlopen(B + path).read().decode()
def head(html):
    t = re.search(r'<title>([^<]*)', html); d = re.search(r'name="description" content="([^"]*)"', html)
    return (t.group(1) if t else '—') + ' | ' + (d.group(1) if d else '—')
async def fill(pg, sel, val):
    """Поля основного языка (az) видны всегда — слева. Поле второго языка (ru или en) видно, когда он выбран справа: сначала выбираем его."""
    m = re.search(r'-(az|ru|en)$', sel)
    if m and not await pg.locator(sel).is_visible(): await pg.locator(f'[data-lg-set={m.group(1)}]').first.click()
    await pg.fill(sel, val)
async def main():
    sql("DELETE FROM ao_logins")
    # файлы для проверки загрузки создаются здесь же: картинка товара и две «обманки»
    from PIL import Image, ImageDraw
    pathlib.Path(f'{ROOT}/test/fake').mkdir(exist_ok=True)
    im = Image.new('RGB', (1200, 800), 'white'); d = ImageDraw.Draw(im)
    d.ellipse((250, 250, 550, 550), outline=(29, 95, 209), width=26); d.ellipse((650, 250, 950, 550), outline=(29, 95, 209), width=26); d.line((550, 400, 650, 400), fill=(29, 95, 209), width=22)
    im.save(f'{ROOT}/test/fake/product.jpg', quality=88)
    pathlib.Path(f'{ROOT}/test/fake/evil.php').write_text('<?php echo "x"; ?>'); pathlib.Path(f'{ROOT}/test/fake/fake.jpg').write_text('<?php echo "not an image"; ?>')
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        errors = []
        ctx = await b.new_context(viewport={'width': 1440, 'height': 900})
        pg = await ctx.new_page()
        pg.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))
        pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
        pg.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
        bad = []
        pg.on('response', lambda r: bad.append(f'{r.status} {r.url.replace(B, "")}') if r.status >= 400 else None)
        tail = lambda: pg.url.replace(B, '')
        flash = lambda: pg.locator('.flash').first.inner_text()
        # вход
        await pg.goto(B + '/admin/'); print('guest →', tail())
        await pg.fill('#login', 'admin'); await pg.fill('#password', 'wrong-password'); await pg.locator('button[type=submit]').click()
        print('wrong password:', await flash(), '|', tail())
        await pg.fill('#login', 'admin'); await pg.fill('#password', PW); await pg.locator('button[type=submit]').click()
        print('login →', tail(), '| h1:', await pg.inner_text('h1'), '| nav:', len(await pg.locator('#adm-nav a').all()), '| groups:', await pg.locator('#adm-nav .nav-group').all_inner_texts(), '| new badge:', await pg.locator('#adm-nav .n-new').all_inner_texts())
        # обзор: плитки с числами и последние заказы
        print('overview tiles:', [' '.join(x.split()) for x in await pg.locator('.tile').all_inner_texts()], '| current:', await pg.locator('#adm-nav a[aria-current=page]').inner_text())
        print('overview last orders:', await pg.locator('.table tbody tr').count(), '|', (await pg.locator('.table tbody tr').first.inner_text()).replace('\n', ' ').replace('\t', ' | ')[:120])
        print('top buttons:', [x.strip() for x in await pg.locator('.top-acts .btn').all_inner_texts()], '| site link:', await pg.locator('.top-acts a.btn-line').get_attribute('href'))
        await pg.screenshot(path=f'{SH}/adm-home.png')
        await pg.locator('.card-side a').click(); await pg.wait_for_load_state(); print('«Все» →', tail(), '| h1:', await pg.inner_text('h1'))
        await pg.screenshot(path=f'{SH}/adm-orders.png')
        # заказы
        rows = await pg.locator('.table tbody tr').count(); print('orders rows:', rows, '|', (await pg.locator('.table tbody tr').first.inner_text()).replace('\n', ' ').replace('\t', ' | ')[:110])
        await pg.fill('input[name=q]', 'лейла'); await pg.locator('.filter button').click(); print('orders search «лейла»:', await pg.locator('.table tbody tr').count(), '|', tail())
        await pg.goto(B + '/admin/?p=orders')
        await pg.locator('.tabs a', has_text='Заказы').first.click(); print('filter orders:', tail(), await pg.locator('.table tbody tr').count())
        await pg.locator('.table tbody tr a').first.click()
        print('order page:', await pg.inner_text('h1'), '| items rows:', await pg.locator('.table tbody tr').count(), '| comment escaped:', '<b>x</b>' in await pg.inner_text('.msg'), '| no raw tag:', await pg.locator('.msg b').count() == 0)
        await pg.screenshot(path=f'{SH}/adm-order.png')
        await pg.select_option('#status', 'work'); await pg.locator('.panel .btn').click(); print('status:', await flash(), '| db:', sql("SELECT status FROM ao_orders WHERE kind='order' ORDER BY id DESC LIMIT 1"))
        # клиенты: один человек — одна строка, сколько раз обращался и на какую сумму
        await pg.locator('#adm-nav a', has_text='Клиенты').click(); await pg.wait_for_load_state()
        print('clients:', await pg.locator('.table tbody tr').count(), '|', [' '.join(x.split())[:70] for x in await pg.locator('.table tbody tr').all_inner_texts()])
        await pg.locator('.table tbody tr .btn').last.click(); await pg.wait_for_load_state(); print('client → orders:', tail(), '| rows:', await pg.locator('.table tbody tr').count())
        # страницы: список, надписи на трёх языках, заголовки для поисковиков
        await pg.locator('#adm-nav a', has_text='Страницы').click(); await pg.wait_for_load_state()
        print('pages:', await pg.locator('.table tbody tr').count(), '|', [' '.join(x.split())[:60] for x in await pg.locator('.table tbody tr').all_inner_texts()][:3])
        await pg.screenshot(path=f'{SH}/adm-pages.png')
        await pg.locator('.table tbody tr .acts a').first.click(); await pg.wait_for_load_state()
        print('page editor:', await pg.inner_text('.card-head h2'), '| address:', await pg.input_value('.addr input'), '| blocks:', await pg.locator('h3.block').all_inner_texts(), '| fields:', await pg.locator('.field .langs').count())
        # перевод в две колонки: слева всегда основной язык сайта (AZ), справа второй язык — по кнопке RU или EN
        VIS = "[...document.querySelectorAll('[name^=\"t[hero.title]\"]')].filter(x => x.offsetParent).map(x => x.lang + '@' + Math.round(x.getBoundingClientRect().left) + ',' + Math.round(x.getBoundingClientRect().top))"
        print('translation columns: left', await pg.inner_text('.lg-main'), '| buttons:', await pg.locator('.lg-btn').all_inner_texts(), '| right:', await pg.evaluate("document.documentElement.getAttribute('data-lg')"),
              '| visible inputs of hero.title (lang@left,top):', await pg.evaluate(VIS))
        await pg.locator('[data-lg-set=en]').first.click()
        print('after EN:', await pg.evaluate("document.documentElement.getAttribute('data-lg')"), '| pressed:', await pg.evaluate("[...document.querySelectorAll('.lg-btn')].map(b => b.textContent + '=' + b.getAttribute('aria-pressed'))"), '| visible:', await pg.evaluate(VIS))
        await pg.set_viewport_size({'width': 390, 'height': 800}); print('phone: columns one under another:', await pg.evaluate(VIS), '| sideways scroll:', await pg.evaluate('document.documentElement.scrollWidth - innerWidth'))
        await pg.set_viewport_size({'width': 1440, 'height': 900}); await pg.locator('[data-lg-set=ru]').first.click()
        print('seo placeholder:', (await pg.get_attribute('#f-seo-title--ru', 'placeholder'))[:60], '| counter:', await pg.inner_text('.lang[data-lg=ru] .count >> nth=0'))
        await fill(pg, '#f-t-hero-title--ru', 'Очки и линзы в Баку — проверка админки'); await fill(pg, '#f-t-hero-title--az', 'Bakıda eynək və linzalar — yoxlama'); await fill(pg, '#f-seo-title--ru', 'Оптика Asioptik в Баку: очки, линзы, ремонт')
        await fill(pg, '#f-seo-desc--ru', 'Свой текст описания главной страницы для поисковиков: оправы, линзы и ремонт очков в Баку.'); await fill(pg, '#f-t-fact2--ru', 'Доставка бесплатно')
        print('right column after az and ru edits:', await pg.evaluate("document.documentElement.getAttribute('data-lg')"), '| counter:', await pg.inner_text('.lang[data-lg=ru] .count >> nth=0'))
        await pg.locator('.actions .btn').click(); await pg.wait_for_load_state()
        print('lost {freeFrom}:', await flash(), '|', await pg.locator('.field.is-invalid .err').first.inner_text(), '| kept typed title:', await pg.input_value('#f-t-hero-title--ru'))
        await fill(pg, '#f-t-fact2--ru', 'Бесплатная доставка от {freeFrom}'); await pg.locator('.actions .btn').click(); await pg.wait_for_load_state()
        print('page saved:', await flash(), '| db texts:', sql("SELECT value FROM ao_settings WHERE name='texts'")[:170])
        print('db seo:', sql("SELECT value FROM ao_settings WHERE name='seo'")[:170])
        await pg.goto(B + '/admin/?p=pages'); print('pages status:', ' '.join((await pg.locator('.table tbody tr').first.inner_text()).split()))
        html = raw('/ru'); print('server head ru:', head(html)[:150]); print('server head az:', head(raw('/'))[:110])
        # на другой странице справа остаётся тот же язык, что выбран
        await pg.goto(B + '/admin/?p=page&id=catalog'); print('right column kept on next page:', await pg.evaluate("document.documentElement.getAttribute('data-lg')"), '| catalog blocks:', await pg.locator('h3.block').all_inner_texts())
        await fill(pg, '#f-seo-title--ru', 'Каталог очков и линз — Asioptik'); await pg.locator('.actions .btn').click(); await pg.wait_for_load_state()
        print('catalog seo:', await flash(), '|', head(raw('/ru/catalog'))[:80], '| section page keeps its own:', head(raw('/ru/catalog?cat=frames'))[:40])
        # товары: список, разделы-кнопки, поиск, правка цены, фото
        await pg.locator('#adm-nav a', has_text='Товары').click(); print('products:', await pg.locator('.table tbody tr').count(), '| add button:', (await pg.inner_text('.top-acts a.btn:not(.btn-line)')).strip(), '| chips:', await pg.locator('.tabs a').all_inner_texts())
        print('product row:', ' | '.join(' '.join(x.split()) for x in await pg.locator('.table tbody tr >> nth=0').locator('td').all_inner_texts()), '| seo dots:', await pg.locator('.table td .dot-ok').count(), '/', await pg.locator('.table td .dot').count())
        await pg.screenshot(path=f'{SH}/adm-products.png')
        await pg.locator('.tabs a', has_text='Контактные линзы').click(); await pg.wait_for_load_state(); print('chip «Контактные линзы»:', await pg.locator('.table tbody tr').count(), '|', tail())
        await pg.locator('.tabs a', has_text='Все').click(); await pg.wait_for_load_state()
        await pg.fill('input[name=q]', 'милан'); await pg.locator('.filter button').click(); print('search «милан»:', await pg.locator('.table tbody tr').count())
        print('row buttons:', [x.strip() for x in await pg.locator('.table tbody tr .acts .btn').all_inner_texts()], '| open:', await pg.locator('.table tbody tr .acts a').first.get_attribute('href'))
        await pg.locator('.table tbody tr a.strong').first.click(); print('edit:', await pg.inner_text('h1'), '|', await pg.inner_text('.card-head h2'), '| title:', await pg.title())
        print('seo auto text:', (await pg.get_attribute('#f-seoTitle-ru', 'placeholder')), '|', (await pg.get_attribute('#f-seoDesc-ru', 'placeholder'))[:70], '| counters:', await pg.locator('.lang[data-lg=ru] .count').all_inner_texts())
        await pg.screenshot(path=f'{SH}/adm-product-edit.png', full_page=True)
        await pg.fill('#f-price', '149'); await pg.fill('#f-old', '199')
        await pg.set_input_files('input[name="file[img]"]', f'{ROOT}/test/fake/product.jpg')
        await fill(pg, '#f-seoTitle-ru', 'Оправа «Милан» из ацетата — купить в Баку')
        await pg.locator('.actions .btn').click(); print('save:', await flash(), '| db price:', sql("SELECT JSON_EXTRACT(data, '$.price', '$.old', '$.img', '$.opts', '$.art') FROM ao_items WHERE type='product' AND slug='f-milan'")[:110])
        # большое фото с телефона уменьшается ещё в браузере; у PNG сохраняется прозрачный фон
        from PIL import Image
        Image.effect_noise((4000, 3000), 70).convert('RGB').save(f'{ROOT}/test/fake/big-phone.jpg', quality=93)
        cut = Image.new('RGBA', (2600, 1800), (0, 0, 0, 0)); cut.paste(Image.effect_noise((1800, 1000), 80).convert('RGBA'), (400, 400)); cut.save(f'{ROOT}/test/fake/cutout.png')
        mid = sql("SELECT id FROM ao_items WHERE type='product' AND slug='f-milan'")
        for fn in ('big-phone.jpg', 'cutout.png'):
            await pg.goto(B + f'/admin/?p=edit&type=product&id={mid}')
            await pg.set_input_files('input[name="file[img]"]', f'{ROOT}/test/fake/{fn}')
            for _ in range(100):   # ждём, пока браузер подготовит фото
                if await pg.evaluate("(() => { const p = document.querySelector('.file-note'); return !!p && !p.hidden && !/Готовлю/.test(p.textContent); })()"): break
                await pg.wait_for_timeout(100)
            noted = await pg.inner_text('.file-note'); sent = await pg.evaluate("(() => { const f = document.querySelector('input[name=\"file[img]\"]').files[0]; return f.name + ' ' + f.type + ' ' + Math.round(f.size / 1024) + ' KB'; })()")
            thumb = await pg.evaluate("(document.querySelector('.imgf .thumb') || {src: ''}).src.slice(0, 5)")
            await pg.locator('.actions .btn').click(); await pg.wait_for_load_state()
            stored = sql(f"SELECT JSON_UNQUOTE(JSON_EXTRACT(data, '$.img')) FROM ao_items WHERE id={mid}"); im = Image.open(f'{ROOT}/site/{stored}')
            print(f'shrink {fn}: {noted} | sent {sent} | preview {thumb} | stored {stored[-5:]} {im.size} {im.mode}' + (f' corner alpha {im.convert("RGBA").getpixel((5, 5))[3]}' if fn.endswith('png') else ''), '| original', pathlib.Path(f'{ROOT}/test/fake/{fn}').stat().st_size // 1024, 'KB')
            pathlib.Path(f'{ROOT}/test/fake/{fn}').unlink()
        print('product seo on site:', head(raw('/ru/product/f-milan'))[:110]); print('product seo, az stays automatic:', head(raw('/product/f-milan'))[:60])
        # загрузка не-картинки
        await pg.goto(B + f'/admin/?p=edit&type=product&id={mid}')
        await pg.set_input_files('input[name="file[img]"]', f'{ROOT}/test/fake/fake.jpg'); await pg.locator('.actions .btn').click()
        print('fake image:', (await pg.locator('.err').first.inner_text()), '| still on edit:', 'p=edit' in tail())
        await pg.set_input_files('input[name="file[img]"]', f'{ROOT}/test/fake/evil.php'); await pg.wait_for_timeout(200)
        print('php file chosen:', await pg.inner_text('.file-note'), '| still selected:', await pg.evaluate("document.querySelector('input[name=\"file[img]\"]').files.length"))
        # пустое название
        await pg.locator('[data-lg-set=en]').first.click(); await fill(pg, '#f-name-az', ''); await pg.locator('.actions .btn').click(); await pg.wait_for_load_state()
        print('empty name:', await pg.locator('.field.is-invalid .err').first.inner_text(), '| the empty field (az) is in view:', await pg.locator('#f-name-az').is_visible(), '| right column stays:', await pg.evaluate("document.documentElement.getAttribute('data-lg')"))
        await pg.locator('[data-lg-set=ru]').first.click()
        # новый бренд и новый товар
        await pg.goto(B + '/admin/?p=edit&type=brand'); await pg.fill('#f-name', 'Baku Vision'); await pg.locator('.actions .btn').click(); print('brand:', await flash(), '|', sql("SELECT slug FROM ao_items WHERE type='brand' ORDER BY id DESC LIMIT 1"))
        await pg.goto(B + '/admin/?p=edit&type=product'); print('new product starts with:', await pg.locator('.choose a').all_inner_texts())
        await pg.locator('.choose a').first.click(); print('frames form: withLenses checked:', await pg.is_checked('input[name="f[withLenses]"]'), '| cat:', await pg.input_value('#f-cat'))
        await fill(pg, '#f-name-az', '«Xəzər» çərçivəsi'); await fill(pg, '#f-name-ru', 'Оправа «Хазар»'); await fill(pg, '#f-name-en', 'Khazar frame'); await fill(pg, '#f-sub-ru', 'Ацетат, квадратная')
        await pg.select_option('#f-brand', 'baku-vision'); await pg.locator('input[name="f[for][]"][value=men]').check()
        await pg.fill('#f-price', '115'); await pg.fill('input[name="f[colors][0][n][ru]"]', 'Чёрный'); await pg.fill('input[name="f[colors][0][n][az]"]', 'Qara'); await pg.fill('input[name="f[colors][0][c]"]', '#1f1f22')
        await fill(pg, '#f-info-ru', 'Материал: Ацетат\nВес: 22 г'); await pg.locator('input[name="f[home]"]').check()
        await pg.locator('.actions .btn').click(); print('new product:', await flash(), '|', sql("SELECT CONCAT(slug, ' | ', JSON_EXTRACT(data, '$.art', '$.withLenses', '$.brand', '$.for', '$.info.ru')) FROM ao_items WHERE type='product' ORDER BY id DESC LIMIT 1")[:150])
        await pg.goto(B + '/admin/?p=edit&type=product&cat=care'); await fill(pg, '#f-name-az', 'Sprey'); await fill(pg, '#f-name-ru', 'Спрей для очков'); await pg.fill('#f-price', '7'); await pg.locator('input[name="f[withLenses]"]').check(); await pg.locator('.actions .btn').click()
        print('care product:', sql("SELECT CONCAT(slug, ' withLenses=', IFNULL(JSON_EXTRACT(data, '$.withLenses'), 'нет'), ' art=', JSON_EXTRACT(data, '$.art')) FROM ao_items WHERE type='product' ORDER BY id DESC LIMIT 1"))
        # дубликат
        pid = sql("SELECT id FROM ao_items WHERE type='product' AND slug='c-daily'")
        await pg.goto(B + f'/admin/?p=edit&type=product&copy={pid}'); await fill(pg, '#f-name-ru', 'Однодневные линзы Плюс'); await fill(pg, '#f-name-az', 'Birgünlük linzalar Plus'); await fill(pg, '#f-name-en', 'Daily lenses Plus'); await pg.fill('#f-price', '44')
        await pg.locator('.actions .btn').click(); print('copy:', await flash(), '|', sql("SELECT CONCAT(slug, ' | opts: ', JSON_LENGTH(data, '$.opts')) FROM ao_items WHERE type='product' ORDER BY id DESC LIMIT 1"))
        # статья блога
        await pg.goto(B + '/admin/?p=edit&type=post'); await pg.fill('#f-date', '2026-11-20'); await fill(pg, '#f-title-az', 'Linza seçimi'); await fill(pg, '#f-title-ru', 'Как выбрать линзы')
        await fill(pg, '#f-lead-ru', 'Коротко о выборе.'); await fill(pg, '#f-body-ru', '## Первое\nАбзац текста.\n- пункт один\n- пункт два'); await fill(pg, '#f-body-az', 'Mətn.')
        await fill(pg, '#f-cta-text-ru', 'В каталог'); await fill(pg, '#f-cta-text-az', 'Kataloqa'); await pg.select_option('#f--link', 'catalog:lenses')
        await pg.locator('.actions .btn').click(); print('post:', await flash(), '|', sql("SELECT CONCAT(slug, ' | ', JSON_EXTRACT(data, '$.cta')) FROM ao_items WHERE type='post' ORDER BY id DESC LIMIT 1")[:140])
        # услуга, раздел, настройки, о нас, баннеры
        sid = sql("SELECT id FROM ao_items WHERE type='service' AND slug='clean'")
        await pg.goto(B + f'/admin/?p=edit&type=service&id={sid}'); await pg.fill('#f-price', '4'); await pg.locator('.actions .btn').click(); print('service:', await flash())
        await pg.goto(B + '/admin/?p=list&type=category'); print('categories:', await pg.locator('.table tbody tr').count(), '| add button:', await pg.locator('.top-acts a.btn:not(.btn-line)').count(), '| delete buttons:', await pg.locator('.btn-del').count())
        # слайды первого экрана: временное фото можно убрать, своё фото заменяет временное вместе с его кадрированием
        care = sql("SELECT id FROM ao_items WHERE type='category' AND slug='care'"); sun = sql("SELECT id FROM ao_items WHERE type='category' AND slug='sun'")
        print('slide photos from the stock:', sql("SELECT GROUP_CONCAT(CONCAT(slug, ':', IF(JSON_EXTRACT(data, '$.banner.demo') IS NULL, 'нет', 'есть')) ORDER BY position SEPARATOR ' ') FROM ao_items WHERE type='category'"), '| data version:', sql("SELECT value FROM ao_settings WHERE name='data_version'"))
        await pg.goto(B + f'/admin/?p=edit&type=category&id={care}'); print('category form offers to remove it:', await pg.locator('input[name=nodemo]').count())
        await pg.check('input[name=nodemo]'); await pg.locator('.actions .btn').click(); await pg.wait_for_load_state()
        print('temporary photo removed:', await flash(), '| left:', sql(f"SELECT IFNULL(JSON_EXTRACT(data, '$.banner.demo', '$.banner.pos', '$.banner.flip'), 'ничего') FROM ao_items WHERE id={care}"))
        await pg.goto(B + f'/admin/?p=edit&type=category&id={sun}'); await pg.set_input_files('input[name="file[banner.img]"]', f'{ROOT}/test/fake/product.jpg'); await pg.locator('.actions .btn').click(); await pg.wait_for_load_state()
        print('own slide photo:', await flash(), '|', sql(f"SELECT JSON_EXTRACT(data, '$.banner.img') FROM ao_items WHERE id={sun}"), '| temporary left:', sql(f"SELECT IFNULL(JSON_EXTRACT(data, '$.banner.demo', '$.banner.pos', '$.banner.flip'), 'ничего') FROM ao_items WHERE id={sun}"))
        await pg.goto(B + f'/admin/?p=edit&type=category&id={sun}'); print('no checkbox once the photo is own:', await pg.locator('input[name=nodemo]').count())
        await pg.goto(B + '/admin/?p=doc&name=config'); await pg.fill('#f-phone', '+994 50 555 44 33'); await pg.fill('#f-whatsapp', '+994 (50) 555-44-33'); await pg.fill('#f-freeDeliveryFrom', '200')
        await pg.locator('.actions .btn').click(); print('settings:', await flash(), '|', sql("SELECT JSON_EXTRACT(value, '$.whatsapp', '$.phone', '$.freeDeliveryFrom') FROM ao_settings WHERE name='config'"))
        await pg.screenshot(path=f'{SH}/adm-settings.png', full_page=True)
        await pg.fill('#f-whatsapp', '12'); await pg.locator('.actions .btn').click(); print('bad whatsapp:', await pg.locator('.err').first.inner_text())
        await pg.goto(B + '/admin/?p=doc&name=about'); await pg.set_input_files('input[name="file[img]"]', f'{ROOT}/test/fake/product.jpg'); await pg.locator('.actions .btn').click(); print('about:', await flash())
        await pg.goto(B + '/admin/?p=banners'); print('banner fields:', await pg.locator('input[type=file]').count(), '| temp photos:', await pg.locator('input[name^=nodemo]').count())
        await pg.set_input_files('input[name="file[1.img]"]', f'{ROOT}/test/fake/product.jpg'); await pg.locator('.actions .btn').click(); print('banners:', await flash(), '|', sql("SELECT JSON_EXTRACT(value, '$[1].img') FROM ao_settings WHERE name='audiences'"))
        await pg.screenshot(path=f'{SH}/adm-banners.png')
        # баннер «Для взрослых»: свой заголовок, строка под ним, своё фото вместо первого временного, второе временное убрано
        await fill(pg, '#f-0-head-ru', 'Коллекция осени'); await fill(pg, '#f-0-feats-ru', 'Оправы\nОчки от солнца'); await fill(pg, '#f-0-parts-0-col-ru', 'Мужчинам')
        await pg.set_input_files('input[name="file[0.slides.0.img]"]', f'{ROOT}/test/fake/product.jpg'); await pg.check('input[name="nodemo[0.slides.1]"]')
        await pg.locator('.actions .btn').click(); await pg.wait_for_load_state()
        print('adults banner:', await flash(), '|', sql("SELECT JSON_EXTRACT(value, '$[0].head.ru', '$[0].feats.ru', '$[0].slides[0].img', '$[0].slides[1].demo', '$[0].parts[0].col.ru') FROM ao_settings WHERE name='audiences'")[:200])
        # скрытый товар, удаление товара
        kid = sql("SELECT id FROM ao_items WHERE type='product' AND slug='sprey-dlya-ochkov'")
        await pg.goto(B + f'/admin/?p=edit&type=product&id={kid}'); await pg.locator('input[name=active]').uncheck(); await pg.locator('.actions .btn').click(); print('hide product:', await flash(), '| active:', sql(f"SELECT active FROM ao_items WHERE id={kid}"))
        await pg.goto(B + '/admin/?p=list&type=product&q=спрей'); print('hidden product in list:', ' '.join((await pg.locator('.table tbody tr').first.inner_text()).split())[:60])
        await pg.locator('.table tbody tr .btn-del').first.click(); await pg.wait_for_timeout(500); print('delete product from list:', await flash(), '| left:', sql(f"SELECT COUNT(*) FROM ao_items WHERE id={kid}"), '|', tail())
        cid = sql("SELECT id FROM ao_items WHERE type='product' AND slug='daily-lenses-plus'")
        await pg.goto(B + f'/admin/?p=edit&type=product&id={cid}'); print('copy link on product page:', await pg.locator('p.danger a').inner_text())
        await pg.locator('form.danger button').click(); await pg.wait_for_timeout(500); print('delete product from its page:', await flash(), '| left:', sql(f"SELECT COUNT(*) FROM ao_items WHERE id={cid}"))
        # смена пароля
        await pg.goto(B + '/admin/?p=password'); await pg.fill('#old', 'not-the-password'); await pg.fill('#new', 'New-Pass-2026'); await pg.fill('#new2', 'New-Pass-2026'); await pg.locator('form.narrow .btn').click(); print('password, wrong old:', await flash())
        await pg.fill('#old', PW); await pg.fill('#new', 'short'); await pg.fill('#new2', 'short'); await pg.evaluate("document.querySelector('#new').removeAttribute('minlength')"); await pg.locator('form.narrow .btn').click(); print('password, short:', await flash())
        await pg.fill('#old', PW); await pg.fill('#new', 'New-Pass-2026'); await pg.fill('#new2', 'New-Pass-2026'); await pg.locator('form.narrow .btn').click(); print('password changed:', await flash())
        await pg.fill('#old', 'New-Pass-2026'); await pg.fill('#new', PW); await pg.fill('#new2', PW); await pg.locator('form.narrow .btn').click(); print('password back:', await flash())
        # удаление записи заказа и выход
        mid = sql("SELECT id FROM ao_orders WHERE kind='message' ORDER BY id DESC LIMIT 1")
        await pg.goto(B + f'/admin/?p=order&id={mid}'); await pg.locator('.danger button').click(); await pg.wait_for_timeout(400); print('delete message:', await flash(), '| left:', sql("SELECT COUNT(*) FROM ao_orders"))
        print('http errors:', bad or 'none'); print('console:', errors or 'none')
        # то же самое глазами посетителя
        from run import setup, FORGET
        site = await (await b.new_context(viewport={'width': 1440, 'height': 900})).new_page(); await setup(site); await site.route('https://images.pexels.com/**', lambda r: r.abort())
        await site.goto(B + '/ru'); await site.wait_for_timeout(1200)
        print('site, changed texts ru:', await site.inner_text('h1'), '|', await site.title(), '| fact:', await site.evaluate("[...document.querySelectorAll('body *:not(script):not(style)')].filter(x => !x.children.length && /Бесплатная доставка от/.test(x.textContent)).map(x => x.textContent.trim())[0] || 'нет'"))
        await site.evaluate(FORGET); await site.goto(B + '/'); await site.wait_for_timeout(900); print('site, changed texts az:', await site.inner_text('h1'), '| en untouched:', end=' ')
        await site.goto(B + '/en'); await site.wait_for_timeout(900); print(await site.inner_text('h1'))
        await site.goto(B + '/ru/catalog'); await site.wait_for_timeout(900); print('site, catalog title:', await site.title())
        await site.goto(B + '/ru/product/f-milan'); await site.wait_for_timeout(900); print('site, product title:', await site.title())
        await site.goto(B + '/ru'); await site.wait_for_timeout(1200)
        print('site, slides:', await site.evaluate("""[...document.querySelectorAll('.hero-inner:not(.is-clone) .hs-slide.bn')].map(s => { const im = s.querySelector('.ph'), u = im ? (im.getAttribute('src') || im.getAttribute('data-src')) : ''; return s.className.split(' ')[2].slice(3) + ': ' + (!im ? 'рисунок' : u.indexOf('/uploads/') === 0 ? 'своё фото' : 'временное фото' + (im.classList.contains('is-flip') ? ' (зеркально)' : '')); })"""))
        await site.locator('#adults .sb').scroll_into_view_if_needed(); await site.wait_for_timeout(1200)
        print('site, adults banner:', await site.evaluate("""() => { const sb = document.querySelector('#adults .sb'); return { h2: sb.querySelector('h2').textContent.replace(/\\s+/g, ' ').trim(), feats: [...sb.querySelectorAll('.sb-feats li')].map(x => x.textContent), buttons: [...sb.querySelectorAll('.sb-cta a')].map(x => x.textContent), photos: [...sb.querySelectorAll(':scope > .ph')].map(x => x.getAttribute('src')), dots: sb.querySelectorAll('.sb-dot').length, shown: sb.classList.contains('has-photo') }; }"""))
        await site.locator('#kids .sb').scroll_into_view_if_needed(); await site.wait_for_timeout(1200)
        print('site, kids banner:', await site.evaluate("""() => { const sb = document.querySelector('#kids .sb'); return { title: sb.querySelector('h2').textContent, photo: (sb.querySelector(':scope > .ph') || { getAttribute: () => 'нет' }).getAttribute('src'), shown: sb.classList.contains('has-photo') }; }"""))
        await site.locator('#kids .sb').screenshot(path=f'{SH}/php-kids-banner.png')
        pathlib.Path(f'{ROOT}/test/fake/evil.php').unlink(); pathlib.Path(f'{ROOT}/test/fake/fake.jpg').unlink()
        await pg.locator('.logout button').click(); print('logout →', tail()); await pg.goto(B + '/admin/?p=list&type=product'); print('after logout →', tail())
        await ctx.close()
        # телефон
        ctx = await b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        pg = await ctx.new_page(); await pg.goto(B + '/admin/'); await pg.fill('#login', 'admin'); await pg.fill('#password', PW); await pg.locator('button[type=submit]').click()
        ox = "document.documentElement.scrollWidth - innerWidth"
        print('m overview overflow:', await pg.evaluate(ox)); await pg.locator('.menu-btn').click(); await pg.wait_for_timeout(200); await pg.screenshot(path=f'{SH}/adm-m-menu.png')
        for name, url in (('orders', '?p=orders'), ('products', '?p=list&type=product'), ('pages', '?p=pages'), ('page', '?p=page&id=home'), ('clients', '?p=clients')):
            await pg.goto(B + '/admin/' + url); print(f'm {name} overflow:', await pg.evaluate(ox), end=' | ')
        print()
        await pg.goto(B + '/admin/?p=edit&type=product&id=' + sql("SELECT id FROM ao_items WHERE type='product' AND slug='f-milan'")); print('m edit overflow:', await pg.evaluate(ox)); await pg.screenshot(path=f'{SH}/adm-m-edit.png')
        await ctx.close(); await b.close()
asyncio.run(main())
