"""Админ-панель: вход, заказы, товары, бренды, статьи, настройки, загрузка фото и защита."""
import asyncio, pathlib, re, subprocess
from playwright.async_api import async_playwright
from run import ROOT
B = 'http://127.0.0.1:8771'
SH = f'{ROOT}/shots'
PW = 'Test-Admin-2026'
def sql(q):
    return subprocess.run(['mariadb', '--socket=/tmp/mysql-run/mysqld.sock', '-uroot', 'asioptik_test', '-N', '-e', q], capture_output=True, text=True).stdout.strip()
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
        print('login →', tail(), '| h1:', await pg.inner_text('h1'), '| nav:', len(await pg.locator('#adm-nav a').all()), '| new badge:', await pg.locator('#adm-nav .n').all_inner_texts())
        await pg.screenshot(path=f'{SH}/adm-orders.png')
        # заказы
        rows = await pg.locator('.table tbody tr').count(); print('orders rows:', rows, '|', (await pg.locator('.table tbody tr').first.inner_text()).replace('\n', ' ').replace('\t', ' | ')[:110])
        await pg.locator('.tabs a', has_text='Заказы').first.click(); print('filter orders:', tail(), await pg.locator('.table tbody tr').count())
        await pg.locator('.table tbody tr a').first.click()
        print('order page:', await pg.inner_text('h1'), '| items rows:', await pg.locator('.table tbody tr').count(), '| comment escaped:', '<b>x</b>' in await pg.inner_text('.msg'), '| no raw tag:', await pg.locator('.msg b').count() == 0)
        await pg.screenshot(path=f'{SH}/adm-order.png')
        await pg.select_option('#status', 'work'); await pg.locator('.panel .btn').click(); print('status:', await flash(), '| db:', sql("SELECT status FROM ao_orders WHERE kind='order' ORDER BY id DESC LIMIT 1"))
        # товары: список, правка цены, фото
        await pg.locator('#adm-nav a', has_text='Товары').click(); print('products:', await pg.locator('.table tbody tr').count())
        await pg.screenshot(path=f'{SH}/adm-products.png')
        await pg.fill('input[name=q]', 'милан'); await pg.locator('.filter button').click(); print('search «милан»:', await pg.locator('.table tbody tr').count())
        await pg.locator('.table tbody tr a').first.click(); print('edit:', await pg.inner_text('h1'))
        await pg.screenshot(path=f'{SH}/adm-product-edit.png', full_page=True)
        await pg.fill('#f-price', '149'); await pg.fill('#f-old', '199')
        await pg.set_input_files('input[name="file[img]"]', f'{ROOT}/test/fake/product.jpg')
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
        # загрузка не-картинки
        await pg.goto(B + f'/admin/?p=edit&type=product&id={mid}')
        await pg.set_input_files('input[name="file[img]"]', f'{ROOT}/test/fake/fake.jpg'); await pg.locator('.actions .btn').click()
        print('fake image:', (await pg.locator('.err').first.inner_text()), '| still on edit:', 'p=edit' in tail())
        await pg.set_input_files('input[name="file[img]"]', f'{ROOT}/test/fake/evil.php'); await pg.wait_for_timeout(200)
        print('php file chosen:', await pg.inner_text('.file-note'), '| still selected:', await pg.evaluate("document.querySelector('input[name=\"file[img]\"]').files.length"))
        # пустое название
        await pg.fill('#f-name-az', ''); await pg.locator('.actions .btn').click(); print('empty name:', await pg.locator('.field.is-invalid .err').first.inner_text())
        # новый бренд и новый товар
        await pg.goto(B + '/admin/?p=edit&type=brand'); await pg.fill('#f-name', 'Baku Vision'); await pg.locator('.actions .btn').click(); print('brand:', await flash(), '|', sql("SELECT slug FROM ao_items WHERE type='brand' ORDER BY id DESC LIMIT 1"))
        await pg.goto(B + '/admin/?p=edit&type=product'); print('new product starts with:', await pg.locator('.choose a').all_inner_texts())
        await pg.locator('.choose a').first.click(); print('frames form: withLenses checked:', await pg.is_checked('input[name="f[withLenses]"]'), '| cat:', await pg.input_value('#f-cat'))
        await pg.fill('#f-name-az', '«Xəzər» çərçivəsi'); await pg.fill('#f-name-ru', 'Оправа «Хазар»'); await pg.fill('#f-name-en', 'Khazar frame'); await pg.fill('#f-sub-ru', 'Ацетат, квадратная')
        await pg.select_option('#f-brand', 'baku-vision'); await pg.locator('input[name="f[for][]"][value=men]').check()
        await pg.fill('#f-price', '115'); await pg.fill('input[name="f[colors][0][n][ru]"]', 'Чёрный'); await pg.fill('input[name="f[colors][0][n][az]"]', 'Qara'); await pg.fill('input[name="f[colors][0][c]"]', '#1f1f22')
        await pg.fill('#f-info-ru', 'Материал: Ацетат\nВес: 22 г'); await pg.locator('input[name="f[home]"]').check()
        await pg.locator('.actions .btn').click(); print('new product:', await flash(), '|', sql("SELECT CONCAT(slug, ' | ', JSON_EXTRACT(data, '$.art', '$.withLenses', '$.brand', '$.for', '$.info.ru')) FROM ao_items WHERE type='product' ORDER BY id DESC LIMIT 1")[:150])
        await pg.goto(B + '/admin/?p=edit&type=product&cat=care'); await pg.fill('#f-name-az', 'Sprey'); await pg.fill('#f-name-ru', 'Спрей для очков'); await pg.fill('#f-price', '7'); await pg.locator('input[name="f[withLenses]"]').check(); await pg.locator('.actions .btn').click()
        print('care product:', sql("SELECT CONCAT(slug, ' withLenses=', IFNULL(JSON_EXTRACT(data, '$.withLenses'), 'нет'), ' art=', JSON_EXTRACT(data, '$.art')) FROM ao_items WHERE type='product' ORDER BY id DESC LIMIT 1"))
        # дубликат
        pid = sql("SELECT id FROM ao_items WHERE type='product' AND slug='c-daily'")
        await pg.goto(B + f'/admin/?p=edit&type=product&copy={pid}'); await pg.fill('#f-name-ru', 'Однодневные линзы Плюс'); await pg.fill('#f-name-az', 'Birgünlük linzalar Plus'); await pg.fill('#f-name-en', 'Daily lenses Plus'); await pg.fill('#f-price', '44')
        await pg.locator('.actions .btn').click(); print('copy:', await flash(), '|', sql("SELECT CONCAT(slug, ' | opts: ', JSON_LENGTH(data, '$.opts')) FROM ao_items WHERE type='product' ORDER BY id DESC LIMIT 1"))
        # статья блога
        await pg.goto(B + '/admin/?p=edit&type=post'); await pg.fill('#f-date', '2026-11-20'); await pg.fill('#f-title-az', 'Linza seçimi'); await pg.fill('#f-title-ru', 'Как выбрать линзы')
        await pg.fill('#f-lead-ru', 'Коротко о выборе.'); await pg.fill('#f-body-ru', '## Первое\nАбзац текста.\n- пункт один\n- пункт два'); await pg.fill('#f-body-az', 'Mətn.')
        await pg.fill('#f-cta-text-ru', 'В каталог'); await pg.fill('#f-cta-text-az', 'Kataloqa'); await pg.select_option('#f--link', 'catalog:lenses')
        await pg.locator('.actions .btn').click(); print('post:', await flash(), '|', sql("SELECT CONCAT(slug, ' | ', JSON_EXTRACT(data, '$.cta')) FROM ao_items WHERE type='post' ORDER BY id DESC LIMIT 1")[:140])
        # услуга, раздел, настройки, о нас, баннеры
        sid = sql("SELECT id FROM ao_items WHERE type='service' AND slug='clean'")
        await pg.goto(B + f'/admin/?p=edit&type=service&id={sid}'); await pg.fill('#f-price', '4'); await pg.locator('.actions .btn').click(); print('service:', await flash())
        await pg.goto(B + '/admin/?p=list&type=category'); print('categories:', await pg.locator('.table tbody tr').count(), '| add button:', await pg.locator('.bar .btn').count())
        await pg.goto(B + '/admin/?p=doc&name=config'); await pg.fill('#f-phone', '+994 50 555 44 33'); await pg.fill('#f-whatsapp', '+994 (50) 555-44-33'); await pg.fill('#f-freeDeliveryFrom', '200')
        await pg.locator('.actions .btn').click(); print('settings:', await flash(), '|', sql("SELECT JSON_EXTRACT(value, '$.whatsapp', '$.phone', '$.freeDeliveryFrom') FROM ao_settings WHERE name='config'"))
        await pg.screenshot(path=f'{SH}/adm-settings.png', full_page=True)
        await pg.fill('#f-whatsapp', '12'); await pg.locator('.actions .btn').click(); print('bad whatsapp:', await pg.locator('.err').first.inner_text())
        await pg.goto(B + '/admin/?p=doc&name=about'); await pg.set_input_files('input[name="file[img]"]', f'{ROOT}/test/fake/product.jpg'); await pg.locator('.actions .btn').click(); print('about:', await flash())
        await pg.goto(B + '/admin/?p=banners'); print('banner fields:', await pg.locator('input[type=file]').count(), '| temp photos:', await pg.locator('input[name^=nodemo]').count())
        await pg.set_input_files('input[name="file[1.img]"]', f'{ROOT}/test/fake/product.jpg'); await pg.locator('.actions .btn').click(); print('banners:', await flash(), '|', sql("SELECT JSON_EXTRACT(value, '$[1].img') FROM ao_settings WHERE name='audiences'"))
        await pg.screenshot(path=f'{SH}/adm-banners.png')
        # баннер «Для взрослых»: свой заголовок, строка под ним, своё фото вместо первого временного, второе временное убрано
        await pg.fill('#f-0-head-ru', 'Коллекция осени'); await pg.fill('#f-0-feats-ru', 'Оправы\nОчки от солнца'); await pg.fill('#f-0-parts-0-col-ru', 'Мужчинам')
        await pg.set_input_files('input[name="file[0.slides.0.img]"]', f'{ROOT}/test/fake/product.jpg'); await pg.check('input[name="nodemo[0.slides.1]"]')
        await pg.locator('.actions .btn').click(); await pg.wait_for_load_state()
        print('adults banner:', await flash(), '|', sql("SELECT JSON_EXTRACT(value, '$[0].head.ru', '$[0].feats.ru', '$[0].slides[0].img', '$[0].slides[1].demo', '$[0].parts[0].col.ru') FROM ao_settings WHERE name='audiences'")[:200])
        # скрытый товар, удаление товара
        kid = sql("SELECT id FROM ao_items WHERE type='product' AND slug='sprey-dlya-ochkov'")
        await pg.goto(B + f'/admin/?p=edit&type=product&id={kid}'); await pg.locator('input[name=active]').uncheck(); await pg.locator('.actions .btn').click(); print('hide product:', await flash(), '| active:', sql(f"SELECT active FROM ao_items WHERE id={kid}"))
        await pg.goto(B + f'/admin/?p=edit&type=product&id={kid}'); await pg.locator('form.danger button').click(); await pg.wait_for_timeout(400); print('delete product:', await flash(), '| left:', sql(f"SELECT COUNT(*) FROM ao_items WHERE id={kid}"))
        # смена пароля
        await pg.goto(B + '/admin/?p=password'); await pg.fill('#old', 'not-the-password'); await pg.fill('#new', 'New-Pass-2026'); await pg.fill('#new2', 'New-Pass-2026'); await pg.locator('main .btn').click(); print('password, wrong old:', await flash())
        await pg.fill('#old', PW); await pg.fill('#new', 'short'); await pg.fill('#new2', 'short'); await pg.evaluate("document.querySelector('#new').removeAttribute('minlength')"); await pg.locator('main .btn').click(); print('password, short:', await flash())
        await pg.fill('#old', PW); await pg.fill('#new', 'New-Pass-2026'); await pg.fill('#new2', 'New-Pass-2026'); await pg.locator('main .btn').click(); print('password changed:', await flash())
        await pg.fill('#old', 'New-Pass-2026'); await pg.fill('#new', PW); await pg.fill('#new2', PW); await pg.locator('main .btn').click(); print('password back:', await flash())
        # удаление записи заказа и выход
        mid = sql("SELECT id FROM ao_orders WHERE kind='message' ORDER BY id DESC LIMIT 1")
        await pg.goto(B + f'/admin/?p=order&id={mid}'); await pg.locator('.danger button').click(); await pg.wait_for_timeout(400); print('delete message:', await flash(), '| left:', sql("SELECT COUNT(*) FROM ao_orders"))
        print('http errors:', bad or 'none'); print('console:', errors or 'none')
        # то же самое глазами посетителя
        from run import setup
        site = await (await b.new_context(viewport={'width': 1440, 'height': 900})).new_page(); await setup(site); await site.route('https://images.pexels.com/**', lambda r: r.abort())
        await site.goto(B + '/?lang=ru'); await site.wait_for_timeout(1200); await site.locator('#adults .sb').scroll_into_view_if_needed(); await site.wait_for_timeout(1200)
        print('site, adults banner:', await site.evaluate("""() => { const sb = document.querySelector('#adults .sb'); return { h2: sb.querySelector('h2').textContent.replace(/\\s+/g, ' ').trim(), feats: [...sb.querySelectorAll('.sb-feats li')].map(x => x.textContent), buttons: [...sb.querySelectorAll('.sb-cta a')].map(x => x.textContent), photos: [...sb.querySelectorAll(':scope > .ph')].map(x => x.getAttribute('src')), dots: sb.querySelectorAll('.sb-dot').length, shown: sb.classList.contains('has-photo') }; }"""))
        await site.locator('#kids .sb').scroll_into_view_if_needed(); await site.wait_for_timeout(1200)
        print('site, kids banner:', await site.evaluate("""() => { const sb = document.querySelector('#kids .sb'); return { title: sb.querySelector('h2').textContent, photo: (sb.querySelector(':scope > .ph') || { getAttribute: () => 'нет' }).getAttribute('src'), shown: sb.classList.contains('has-photo') }; }"""))
        await site.locator('#kids .sb').screenshot(path=f'{SH}/php-kids-banner.png')
        pathlib.Path(f'{ROOT}/test/fake/evil.php').unlink(); pathlib.Path(f'{ROOT}/test/fake/fake.jpg').unlink()
        await pg.locator('.side-foot button').click(); print('logout →', tail()); await pg.goto(B + '/admin/?p=list&type=product'); print('after logout →', tail())
        await ctx.close()
        # телефон
        ctx = await b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        pg = await ctx.new_page(); await pg.goto(B + '/admin/'); await pg.fill('#login', 'admin'); await pg.fill('#password', PW); await pg.locator('button[type=submit]').click()
        ox = "document.documentElement.scrollWidth - innerWidth"
        print('m orders overflow:', await pg.evaluate(ox)); await pg.locator('.menu-btn').click(); await pg.wait_for_timeout(200); await pg.screenshot(path=f'{SH}/adm-m-menu.png')
        await pg.goto(B + '/admin/?p=edit&type=product&id=' + sql("SELECT id FROM ao_items WHERE type='product' AND slug='f-milan'")); print('m edit overflow:', await pg.evaluate(ox)); await pg.screenshot(path=f'{SH}/adm-m-edit.png')
        await ctx.close(); await b.close()
asyncio.run(main())
