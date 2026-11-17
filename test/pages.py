"""Страницы сайта: каталог с разделами, «О нас», блог, контакты — переходы, адреса, заголовки, формы."""
import asyncio, json
from playwright.async_api import async_playwright
from run import setup, BASE, ROOT, decode

URL = f'{BASE}/dist/optika-4-lupa.html'
SH = f'{ROOT}/shots'
tail = "location.href.split('/').pop()"


async def info(pg):
    return await pg.evaluate("""() => ({ url: location.href.split('/').pop(), title: document.title, h1: (document.querySelector('#pgTitle') || {}).textContent || '',
      view: Shop.state.view, post: Shop.state.post, cat: Shop.state.cat, aud: Shop.state.aud, y: Math.round(scrollY),
      canon: document.querySelector('link[rel=canonical]').href, cur: [...document.querySelectorAll('#siteNav a[aria-current]')].map(a => a.textContent).join(','),
      cards: document.querySelectorAll('#productsGrid .card').length, gridVisible: !!document.querySelector('#catalog').getClientRects().length,
      ox: document.documentElement.scrollWidth - innerWidth })""")


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        errors = []
        ctx = await b.new_context(viewport={'width': 1440, 'height': 900})
        pg = await ctx.new_page()
        pg.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))
        pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' and 'Failed to load resource' not in m.text else None)
        await setup(pg)
        await pg.goto(URL + '?lang=ru'); await pg.wait_for_timeout(1800)
        i = await info(pg); print('home:', i['url'], '| grid visible on home:', i['gridVisible'], '| tiles on home:', await pg.locator('#cats .ctile').count())
        print('nav:', await pg.locator('#siteNav a:visible').all_inner_texts())
        await pg.locator('#cats').scroll_into_view_if_needed(); await pg.wait_for_timeout(300)
        await pg.locator('#cats').screenshot(path=f'{SH}/pg-home-cats.png')

        # главная → плитка «Контактные линзы» → страница каталога с разделом
        await pg.locator('#cats .ctile-contacts').click(); await pg.wait_for_timeout(500)
        i = await info(pg); print('tile contacts:', {k: i[k] for k in ('url', 'title', 'view', 'cat', 'cards', 'gridVisible', 'cur', 'canon')}, '| catalog top:', round((await pg.locator('#catalog').bounding_box())['y']))
        await pg.locator('#catTabs [data-cat="sun"]').click(); await pg.wait_for_timeout(300)
        i = await info(pg); print('tab sun:', i['url'], '|', i['title'], '| cards', i['cards'])
        # товар из каталога и «Назад»
        await pg.locator('#productsGrid .card-title a').first.click(); await pg.wait_for_timeout(500)
        print('product:', await pg.evaluate(tail), '| page', await pg.evaluate('Shop.state.page'))
        await pg.go_back(); await pg.wait_for_timeout(500)
        i = await info(pg); print('back to catalog:', i['url'], '| view', i['view'], 'cat', i['cat'], 'cards', i['cards'])
        # меню «Каталог» сбрасывает раздел и показывает плитки
        await pg.locator('#siteNav a[data-view="catalog"]:not([data-aud])').click(); await pg.wait_for_timeout(500)
        i = await info(pg); print('nav catalog:', {k: i[k] for k in ('url', 'title', 'h1', 'cat', 'cards', 'y', 'cur')}, '| tiles:', await pg.locator('#pageView .ctile').count())
        await pg.screenshot(path=f'{SH}/pg-catalog.png', full_page=False)
        # «Для кого» попадает в адрес
        await pg.locator('[data-aud-switch] [data-aud="kids"]').first.click(); await pg.wait_for_timeout(300)
        i = await info(pg); print('aud kids:', i['url'], '| cards', i['cards'])

        # «О нас»
        await pg.locator('#siteNav a[data-view="about"]').click(); await pg.wait_for_timeout(500)
        i = await info(pg); print('about:', {k: i[k] for k in ('url', 'title', 'h1', 'view', 'y', 'cur', 'canon', 'gridVisible')})
        await pg.screenshot(path=f'{SH}/pg-about.png', full_page=True)
        await pg.locator('.ab-list a').nth(3).click(); await pg.wait_for_timeout(500)
        i = await info(pg); print('about → repair:', i['url'], '| view', repr(i['view']), '| repair top:', round((await pg.locator('#repair').bounding_box())['y']))
        await pg.go_back(); await pg.wait_for_timeout(400)
        await pg.locator('.ab-list a').nth(1).click(); await pg.wait_for_timeout(500)
        i = await info(pg); print('about → lenses:', i['url'], '| view', i['view'], 'cat', i['cat'], 'cards', i['cards'])

        # блог: список → статья → другая статья → «Назад»
        await pg.locator('#siteNav a[data-view="blog"]').click(); await pg.wait_for_timeout(500)
        i = await info(pg); print('blog:', {k: i[k] for k in ('url', 'title', 'h1', 'cur')}, '| posts:', await pg.locator('.bl-card').count(), '| dates:', await pg.locator('.bl-date').all_inner_texts())
        await pg.screenshot(path=f'{SH}/pg-blog.png', full_page=True)
        await pg.locator('.bl-card h2 a').first.click(); await pg.wait_for_timeout(500)
        i = await info(pg); print('post:', {k: i[k] for k in ('url', 'title', 'h1', 'post', 'y', 'cur', 'canon')}, '| meta:', await pg.locator('.post-meta').inner_text(), '| h2:', await pg.locator('.post-body h2').count(), 'li:', await pg.locator('.post-body li').count())
        await pg.screenshot(path=f'{SH}/pg-post.png', full_page=True)
        await pg.locator('.bl-two .bl-card h3 a').first.click(); await pg.wait_for_timeout(500)
        i = await info(pg); print('other post:', i['url'], '|', i['h1'])
        await pg.go_back(); await pg.wait_for_timeout(500)
        i = await info(pg); print('back:', i['url'], '|', i['h1'])
        await pg.locator('.post-cta a').first.click(); await pg.wait_for_timeout(500)
        i = await info(pg); print('post CTA:', i['url'], '| view', i['view'], 'cat', i['cat'], 'cards', i['cards'])
        # язык на странице статьи
        await pg.go_back(); await pg.wait_for_timeout(400)
        await pg.locator('.hdr-right [data-set-lang=\"en\"]').click(); await pg.wait_for_timeout(500)
        i = await info(pg); print('post EN:', i['url'], '|', i['title'], '|', await pg.locator('.post-meta').inner_text(), '| nav:', await pg.locator('#siteNav a:visible').all_inner_texts())
        await pg.locator('.hdr-right [data-set-lang=\"ru\"]').click(); await pg.wait_for_timeout(400)
        # неизвестная статья → список
        await pg.goto(URL + '?lang=ru&page=blog&post=nope'); await pg.wait_for_timeout(1200)
        i = await info(pg); print('unknown post:', i['h1'], '| post', repr(i['post']), '| canon', i['canon'])

        # контакты и форма
        await pg.locator('#siteNav a[data-view="contacts"]').click(); await pg.wait_for_timeout(600)
        i = await info(pg); print('contacts:', {k: i[k] for k in ('url', 'title', 'h1', 'cur')}, '| address:', await pg.locator('#pageView [data-cfg="address"]').inner_text(), '| map src set:', await pg.evaluate("!!document.querySelector('#pageView iframe[data-cfg-map]').src"))
        await pg.screenshot(path=f'{SH}/pg-contacts.png', full_page=True)
        await pg.locator('#contactForm [type=submit]').click(); await pg.wait_for_timeout(300)
        print('form errors:', await pg.locator('#contactForm .field-error').all_inner_texts())
        await pg.fill('#ctName', 'Айдан'); await pg.fill('#ctMsg', 'Есть ли оправа «Милан» в чёрном цвете?')
        await pg.locator('#ctPhone').click(); await pg.keyboard.type('0551112233'); await pg.select_option('#ctTopic', 'glasses')   # в форме теперь есть телефон и услуга
        print('errors after typing:', [x for x in await pg.locator('#contactForm .field-error').all_inner_texts() if x])
        # смена языка не стирает набранное
        await pg.locator('.hdr-right [data-set-lang=\"az\"]').click(); await pg.wait_for_timeout(400)
        print('kept after lang switch:', await pg.input_value('#ctName'), '|', await pg.input_value('#ctMsg'), '| label:', await pg.locator('label[for=ctMsg]').inner_text())
        await pg.locator('.hdr-right [data-set-lang=\"ru\"]').click(); await pg.wait_for_timeout(400)
        await pg.locator('#contactForm [type=submit]').click(); await pg.wait_for_timeout(500)
        opened = await pg.evaluate('window.__opened')
        path, text = decode(opened[-1]); print('WA →', path, '|', text.replace('\n', ' / '), '| toast:', await pg.locator('#toastText').inner_text(), '| message cleared:', repr(await pg.input_value('#ctMsg')))

        # логотип со страницы ведёт на главную; старые ссылки #catalog открывают страницу каталога
        await pg.locator('.hdr > .logo').click(); await pg.wait_for_timeout(500)
        i = await info(pg); print('logo → home:', i['url'], '| view', repr(i['view']), 'y', i['y'], '| title', i['title'])
        await pg.locator('.hero a[data-goto="frames"]').first.click(); await pg.wait_for_timeout(500)
        i = await info(pg); print('hero CTA:', i['url'], '| view', i['view'], 'cat', i['cat'], 'cards', i['cards'], '| catalog top:', round((await pg.locator('#catalog').bounding_box())['y']))
        await pg.goto(URL + '?lang=ru#catalog'); await pg.wait_for_timeout(1300)
        i = await info(pg); print('old #catalog link:', i['url'], '| view', i['view'], '| grid', i['gridVisible'])
        await pg.goto(URL + '?lang=ru&page=catalog&cat=lenses&aud=kids'); await pg.wait_for_timeout(1300)
        i = await info(pg); print('direct category link:', i['url'], '| cat', i['cat'], 'aud', repr(i['aud']), 'cards', i['cards'], '|', i['title'])
        await pg.goto(URL + '?lang=ru&page=catalog&cat=frames&aud=kids'); await pg.wait_for_timeout(1300)
        i = await info(pg); print('direct frames for kids:', i['url'], '| cards', i['cards'], '| canon', i['canon'])
        # корзина: пустая корзина → «В каталог» со страницы «О нас»
        await pg.goto(URL + '?lang=ru&page=about'); await pg.wait_for_timeout(1200)
        await pg.locator('.site-header [data-open-cart]').first.click(); await pg.wait_for_timeout(400)
        await pg.locator('#cartDrawer a[href="#catalog"]').click(); await pg.wait_for_timeout(600)
        i = await info(pg); print('empty cart → catalog:', i['url'], '| view', i['view'], '| drawer open:', await pg.evaluate("document.querySelector('#cartDrawer').classList.contains('is-open')"))
        await ctx.close()

        # телефон: меню, страницы, переполнение
        ctx = await b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        pg = await ctx.new_page(); pg.on('pageerror', lambda e: errors.append(f'pageerror(m): {e}')); await setup(pg)
        await pg.goto(URL); await pg.wait_for_timeout(1800)
        await pg.locator('.hdr-right .js-menu-toggle').click(); await pg.wait_for_timeout(300)
        print('m menu:', await pg.locator('#siteNav a:visible').all_inner_texts())
        await pg.screenshot(path=f'{SH}/pg-m-menu.png')
        for v in ('catalog', 'about', 'blog', 'contacts'):
            if not await pg.evaluate("document.body.classList.contains('menu-open')"):
                await pg.locator('.hdr-right .js-menu-toggle').click(); await pg.wait_for_timeout(250)
            await pg.locator(f'#siteNav a[data-view="{v}"]:not([data-aud])').click(); await pg.wait_for_timeout(600)
            i = await info(pg); print('m', v, '|', i['url'], '|', i['h1'], '| overflow x:', i['ox'], '| menu open:', await pg.evaluate("document.body.classList.contains('menu-open')"))
            await pg.screenshot(path=f'{SH}/pg-m-{v}.png', full_page=True)
        await pg.goto(URL + '?page=blog&post=prescription'); await pg.wait_for_timeout(1200)
        i = await info(pg); print('m post overflow x:', i['ox']); await pg.screenshot(path=f'{SH}/pg-m-post.png', full_page=True)
        await ctx.close()
        await b.close()
        print('errors:', errors or 'none')

asyncio.run(main())
