"""Бренды, сортировка над товарами, оформление заказа отдельной страницей, форма «Напишите нам» с телефоном, услугой и рецептом."""
import asyncio, re
from playwright.async_api import async_playwright
from run import setup, BASE, ROOT, decode
URL = f'{BASE}/dist/optika-4-lupa.html'
SH = f'{ROOT}/shots'
async def fake(route):
    m = re.search(r'/photos/(\d+)/', route.request.url)
    await route.fulfill(path=f'{ROOT}/test/fake/{m.group(1)}.jpg', content_type='image/jpeg')
tail = lambda pg: pg.url.split('/')[-1]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        errors = []
        ctx = await b.new_context(viewport={'width': 1440, 'height': 900})
        pg = await ctx.new_page()
        pg.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))
        pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' and 'Failed to load resource' not in m.text else None)
        await setup(pg); await pg.route('https://images.pexels.com/**', fake)

        # ---------- каталог: бренды и сортировка ----------
        await pg.goto(URL + '?lang=ru&page=catalog'); await pg.wait_for_timeout(1500)
        cards = lambda: pg.locator('#productsGrid .card').count()
        prices = "[...document.querySelectorAll('#productsGrid .card .price')].map(e => parseFloat(e.textContent.replace(/[^0-9.]/g, ' ').trim().split(/\\s+/)[0]))"
        print('brands:', await pg.locator('#brandList button').all_inner_texts(), '| now:', await pg.inner_text('#catNow'), '|', await pg.inner_text('#resultCount'))
        print('sort buttons:', await pg.locator('.sort-btns button').all_inner_texts(), '| labels:', await pg.evaluate("[...document.querySelectorAll('.sort-btns button')].map(b => b.getAttribute('aria-label') || '')"))
        await pg.locator('[data-sort="asc"]').click(); await pg.wait_for_timeout(200)
        pr = await pg.evaluate(prices); print('price asc:', pr[:6], '… sorted:', pr == sorted(pr), '| pressed:', await pg.get_attribute('[data-sort="asc"]', 'aria-pressed'))
        await pg.locator('[data-sort="desc"]').click(); await pg.wait_for_timeout(200)
        pr = await pg.evaluate(prices); print('price desc:', pr[:6], '… sorted:', pr == sorted(pr, reverse=True))
        await pg.locator('#catalog').scroll_into_view_if_needed(); await pg.wait_for_timeout(300); await pg.screenshot(path=f'{SH}/b2-catalog.png')
        await pg.locator('[data-sort="default"]').click()
        await pg.locator('#brandList [data-brand="asi-sun"]').click(); await pg.wait_for_timeout(200)
        print('brand Asi Sun:', await cards(), '|', tail(pg), '| focus:', await pg.evaluate('document.activeElement.dataset.brand'))
        await pg.locator('#brandList [data-brand="asi-kids"]').click(); await pg.wait_for_timeout(200)
        print('+ Asi Kids:', await cards(), '|', tail(pg), '| card brands:', sorted(set(await pg.locator('#productsGrid .card-brand').all_inner_texts())))
        await pg.locator('#catTabs [data-cat="frames"]').click(); await pg.wait_for_timeout(200)
        # вкладка меняет только раздел: бренды остаются, если они есть в разделе
        print('frames tab:', await cards(), '| brands shown:', await pg.locator('#brandList button').all_inner_texts(), '| active:', await pg.evaluate("Shop.state.brands.join(',')"), '| now:', await pg.inner_text('#catNow'))
        await pg.locator('#catTabs [data-cat="contacts"]').click(); await pg.wait_for_timeout(200)
        print('contacts tab:', await cards(), '| brand box hidden:', await pg.evaluate("document.getElementById('brandBox').hidden"), '|', tail(pg))
        await pg.goto(URL + '?lang=ru&page=catalog&cat=sun&brand=asi-sun'); await pg.wait_for_timeout(1200)
        print('direct brand link:', await cards(), '| active:', await pg.evaluate("Shop.state.brands.join(',')"))
        await pg.fill('#searchInput', 'asi kids'); await pg.wait_for_timeout(400)
        await pg.locator('#catTabs [data-cat="all"]').click(); await pg.locator('#brandList [data-brand="asi-sun"]').click(); await pg.wait_for_timeout(300)
        print('search by brand name:', await cards())
        await pg.goto(URL + '?lang=ru&product=f-milan'); await pg.wait_for_timeout(1000)
        print('product page brand:', await pg.inner_text('.pp-brand'))

        # ---------- оформление заказа — страница ----------
        await pg.locator('#ppAdd').click(); await pg.wait_for_timeout(400)
        await pg.locator('.site-header [data-open-cart]').first.click(); await pg.wait_for_timeout(400)
        await pg.locator('#cartDrawer [data-checkout]').click(); await pg.wait_for_timeout(600)
        print('checkout:', tail(pg), '| title:', await pg.title(), '| h1:', await pg.inner_text('#coTitle'), '| drawer open:', await pg.evaluate("document.querySelector('#cartDrawer').classList.contains('is-open')"),
              '| form visible:', await pg.locator('#checkoutForm').is_visible(), '| items:', await pg.locator('#coItems li').count(), '| total:', await pg.inner_text('#coTotal'), '| y:', await pg.evaluate('scrollY'))
        await pg.screenshot(path=f'{SH}/b2-checkout.png', full_page=True)
        await pg.go_back(); await pg.wait_for_timeout(500); print('back:', tail(pg), '| page', await pg.evaluate('Shop.state.page'))
        await pg.go_forward(); await pg.wait_for_timeout(500); print('forward:', tail(pg), '| view', await pg.evaluate('Shop.state.view'), '| items:', await pg.locator('#coItems li').count())
        await pg.locator('#checkoutForm [type=submit]').click(); await pg.wait_for_timeout(300)
        print('checkout errors:', [x for x in await pg.locator('#checkoutForm .field-error').all_inner_texts() if x])
        await pg.locator('.hdr-right [data-set-lang=\"az\"]').click(); await pg.wait_for_timeout(400)
        print('AZ:', await pg.inner_text('#coTitle'), '| pickup:', (await pg.locator('#checkoutForm .choice').first.inner_text()).split('\n')[0], '| delivery row:', await pg.inner_text('#coDelivery'))
        await pg.locator('.hdr-right [data-set-lang=\"ru\"]').click(); await pg.wait_for_timeout(300)
        await pg.fill('#coName', 'Лейла'); await pg.fill('#coPhone', '0501234567')
        await pg.locator('#checkoutForm [type=submit]').click(); await pg.wait_for_timeout(700)
        path, text = decode((await pg.evaluate('window.__opened'))[-1])
        print('order →', path, '|', ' / '.join(text.split('\n')[:3]), '… |', [l for l in text.split('\n') if 'Получение' in l or 'Доставка' in l])
        print('after order:', tail(pg), '| view', repr(await pg.evaluate('Shop.state.view')), '| success open:', await pg.evaluate("document.querySelector('#successModal').classList.contains('is-open')"), '| cart:', await pg.evaluate('Shop.state.cart.length'))
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(300)
        await pg.goto(URL + '?lang=ru&page=checkout'); await pg.wait_for_timeout(1200)
        print('empty checkout: form visible', await pg.locator('#checkoutForm').is_visible(), '| empty note:', await pg.locator('#coEmpty').is_visible(), '|', (await pg.inner_text('#coEmpty')).replace('\n', ' / ')[:90])
        await pg.locator('#coEmpty a').click(); await pg.wait_for_timeout(500); print('to catalog:', tail(pg))

        # ---------- форма «Напишите нам» ----------
        await pg.goto(URL + '?lang=ru&page=contacts'); await pg.wait_for_timeout(1300)
        await pg.evaluate("localStorage.removeItem('optika4-customer')")
        print('fields:', await pg.evaluate("[...document.querySelectorAll('#contactForm label, #contactForm .ct-label')].map(l => l.textContent.trim().replace(/\\s+/g, ' '))"))
        print('topics:', await pg.locator('#ctTopic option').all_inner_texts())
        await pg.fill('#ctName', ''); await pg.fill('#ctPhone', '')
        await pg.locator('#contactForm [type=submit]').click(); await pg.wait_for_timeout(300)
        print('errors:', [x for x in await pg.locator('#contactForm .field-error').all_inner_texts() if x])
        await pg.fill('#ctName', 'Айдан'); await pg.locator('#ctPhone').click(); await pg.keyboard.type('0551112233'); await pg.select_option('#ctTopic', 'rx')
        print('phone formatted:', await pg.input_value('#ctPhone'), '| errors left:', [x for x in await pg.locator('#contactForm .field-error').all_inner_texts() if x])
        await pg.set_input_files('#ct-photo', f'{ROOT}/shots/kit-a.png'); await pg.wait_for_timeout(400)
        print('photo:', await pg.inner_text('#ctPhotoBox .rx-file-name'), '| thumb:', await pg.locator('#ctPhotoBox img.rx-thumb').count())
        await pg.locator('.ct-write').scroll_into_view_if_needed(); await pg.wait_for_timeout(200); await pg.locator('.ct-form').screenshot(path=f'{SH}/b2-contact-form.png')
        await pg.locator('.hdr-right [data-set-lang=\"en\"]').click(); await pg.wait_for_timeout(400)
        print('kept after lang switch:', await pg.input_value('#ctName'), '|', await pg.input_value('#ctPhone'), '|', await pg.input_value('#ctTopic'), '| photo kept:', await pg.locator('#ctPhotoBox .rx-file-name').count())
        await pg.locator('.hdr-right [data-set-lang=\"ru\"]').click(); await pg.wait_for_timeout(300)
        await pg.locator('#contactForm [type=submit]').click(); await pg.wait_for_timeout(600)
        path, text = decode((await pg.evaluate('window.__opened'))[-1]); print('WA →', path, '|', text.replace('\n', ' / '))
        print('success:', await pg.inner_text('#okTitle'), '|', await pg.inner_text('#okText'), '| photo note:', (await pg.inner_text('#okPhotoText'))[:70], '| photo cleared:', await pg.locator('#ctPhotoBox .rx-drop').count())
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(300)
        await pg.select_option('#ctTopic', 'repair'); await pg.fill('#ctMsg', 'Сломался заушник')
        await pg.locator('#contactForm [type=submit]').click(); await pg.wait_for_timeout(500)
        path, text = decode((await pg.evaluate('window.__opened'))[-1]); print('no photo →', text.replace('\n', ' / '), '| toast:', await pg.inner_text('#toastText'), '| modal:', await pg.evaluate("document.querySelector('#successModal').classList.contains('is-open')"))
        await pg.locator('#ct-photo').focus(); await pg.set_input_files('#ct-photo', f'{ROOT}/shots/kit-a.png'); await pg.wait_for_timeout(300)
        await pg.locator('[data-ct-photo-remove]').click(); await pg.wait_for_timeout(200); print('photo removed:', await pg.locator('#ctPhotoBox .rx-drop').count())

        # ---------- баннер «Для детей» с фото ----------
        await pg.goto(URL + '?lang=ru'); await pg.wait_for_timeout(1200)
        el = pg.locator('#kids .sb'); await el.scroll_into_view_if_needed(); await pg.wait_for_timeout(1000)
        print('kids banner: has photo', await pg.evaluate("document.querySelector('#kids .sb').classList.contains('has-photo')"), '| drawing hidden:', await pg.evaluate("getComputedStyle(document.querySelector('#kids .sb-art')).visibility"))
        await el.screenshot(path=f'{SH}/b2-kids.png')
        await ctx.close()

        # ---------- телефон ----------
        ctx = await b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        pg = await ctx.new_page(); pg.on('pageerror', lambda e: errors.append(f'pageerror(m): {e}')); await setup(pg); await pg.route('https://images.pexels.com/**', fake)
        ox = "document.documentElement.scrollWidth - innerWidth"
        await pg.goto(URL + '?page=catalog'); await pg.wait_for_timeout(1500)
        await pg.locator('#catalog').scroll_into_view_if_needed(); await pg.wait_for_timeout(400)
        print('m catalog overflow:', await pg.evaluate(ox)); await pg.screenshot(path=f'{SH}/b2-m-catalog.png')
        await pg.locator('#productsGrid [data-pid="a-cloth"] [data-add]').click(); await pg.wait_for_timeout(400)
        await pg.goto(URL + '?page=checkout'); await pg.wait_for_timeout(1200)
        print('m checkout overflow:', await pg.evaluate(ox), '| items:', await pg.locator('#coItems li').count()); await pg.screenshot(path=f'{SH}/b2-m-checkout.png', full_page=True)
        await pg.goto(URL + '?page=contacts'); await pg.wait_for_timeout(1200)
        await pg.locator('.ct-form').scroll_into_view_if_needed(); await pg.wait_for_timeout(300)
        print('m contacts overflow:', await pg.evaluate(ox)); await pg.locator('.ct-form').screenshot(path=f'{SH}/b2-m-contact.png')
        await pg.goto(URL); await pg.wait_for_timeout(1200)
        el = pg.locator('#kids .sb'); await el.scroll_into_view_if_needed(); await pg.wait_for_timeout(1000); await el.screenshot(path=f'{SH}/b2-m-kids.png')
        await ctx.close(); await b.close()
        print('errors:', errors or 'none')
asyncio.run(main())
