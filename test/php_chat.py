"""Чат-заявка: кнопка в углу сайта, разговор по шагам и заявка в WhatsApp.

Проверяется: вопросы и подсказки на трёх языках; шаги «что интересует → салон → имя → телефон → дополнение»;
проверки имени и телефона; свой текст вместо подсказки; сообщение для WhatsApp и запись на сервере (раздел
«Заказы»); повторное открытие WhatsApp без второй записи; «Новая заявка» и запомненные имя с телефоном;
шаг «салон» только когда салонов несколько; текст посетителя не становится разметкой; клавиша Escape, смена языка
посреди разговора, телефон; версия сайта одним файлом.

Запуск: sh test/serve.sh, затем python3 test/php_chat.py (базу тест ставит заново сам).
"""
import asyncio, json, pathlib, re, sys, urllib.parse
from playwright.async_api import async_playwright
from run import setup, lp
from php_reset import reset, sql

ROOT = pathlib.Path(__file__).resolve().parent.parent
B = 'http://127.0.0.1:8771'
ONE = 'http://127.0.0.1:8765/dist/optika-4-lupa.html'
fails = []
total = 0
def check(name, ok, detail=''):
    global total
    total += 1
    if not ok:
        fails.append(name)
        print('  FAIL', name, '|', str(detail)[:500])

def last_order():
    """Последняя запись раздела «Заказы»: поля и данные (JSON читается через HEX — в нём переводы строк и кавычки)."""
    head = sql("SELECT CONCAT(kind, '|', status, '|', name, '|', phone, '|', lang) FROM ao_orders ORDER BY id DESC LIMIT 1")
    return head, json.loads(bytes.fromhex(sql('SELECT HEX(data) FROM ao_orders ORDER BY id DESC LIMIT 1')).decode('utf-8'))

TEXT = {
    'az': {'hello': 'Salam! Müraciətinizi bir dəqiqəyə qəbul edirik', 'q': 'Sizi nə maraqlandırır?', 'topics': ['Eynək seçimi', 'Reseptlə eynək linzaları', 'Kontakt linzaları', 'Eynək təmiri', 'Görmə yoxlaması', 'Başqa sual'],
           'branch': 'Hansı salon sizə daha uyğundur?', 'name': 'Sizə necə müraciət edək?', 'send': 'WhatsApp-da göndər', 'open': 'Çatı açın və müraciət buraxın'},
    'ru': {'hello': 'Здравствуйте! Примем заявку за минуту', 'q': 'Что вас интересует?', 'topics': ['Подбор очков', 'Линзы для очков по рецепту', 'Контактные линзы', 'Ремонт очков', 'Проверка зрения', 'Другой вопрос'],
           'branch': 'Какой салон вам удобнее?', 'name': 'Как к вам обращаться?', 'send': 'Отправить в WhatsApp', 'open': 'Открыть чат и оставить заявку'},
    'en': {'hello': 'Hello! We will take your request in a minute', 'q': 'What are you interested in?', 'topics': ['Choosing glasses', 'Prescription lenses for glasses', 'Contact lenses', 'Glasses repair', 'Eye test', 'Something else'],
           'branch': 'Which shop suits you better?', 'name': 'How should we address you?', 'send': 'Send on WhatsApp', 'open': 'Open the chat and leave a request'},
}


async def main():
    print('clean install:', reset())
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        errors = []
        async def new_page(w=1366, h=800, **kw):
            ctx = await b.new_context(viewport={'width': w, 'height': h}, **kw); page = await ctx.new_page()
            page.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))
            page.on('console', lambda m: errors.append(m.text) if m.type == 'error' and '/node_modules/@fontsource/' not in m.text and 'Failed to load resource' not in m.text else None)
            await setup(page); await page.route('https://images.pexels.com/**', lambda r: r.abort())
            return page
        pg = await new_page()
        log = lambda: pg.evaluate("[...document.querySelectorAll('#chatLog .chat-msg')].map(m => (m.classList.contains('me') ? '> ' : '') + m.textContent)")
        chips = lambda: pg.evaluate("[...document.querySelectorAll('#chatLog .chat-chip')].map(c => c.textContent)")
        opened = lambda: pg.evaluate('(window.__opened || []).map(decodeURIComponent)')
        async def go(path):
            await pg.goto(B + path); await pg.wait_for_function('window.Shop'); await pg.wait_for_timeout(300)
        async def say(text):
            await pg.fill('#chatInput', text); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(120)
        async def chip(text):
            await pg.locator('#chatLog .chat-chip', has_text=text).first.click(); await pg.wait_for_timeout(120)

        # 1. кнопка и первые вопросы — на трёх языках
        for l in ('az', 'ru', 'en'):
            await go(lp('/', l)); T = TEXT[l]
            fab = pg.locator('#chatFab')
            check(f'{l}: the corner button is there and says what it does', await fab.is_visible() and await fab.get_attribute('aria-label') == T['open'] and await fab.get_attribute('aria-expanded') == 'false'
                  and await pg.locator('#chatBox').is_hidden(), await fab.get_attribute('aria-label'))
            await fab.click(); await pg.wait_for_timeout(200)
            m = await log()
            check(f'{l}: greeting and the first question', await pg.locator('#chatBox').is_visible() and len(m) == 2 and m[0].startswith(T['hello']) and m[1] == T['q'] and await fab.get_attribute('aria-expanded') == 'true', m)
            check(f'{l}: six topics to choose from', await chips() == T['topics'], await chips())
            await chip(T['topics'][3]); m = await log()
            check(f'{l}: with two shops the next question is the shop', m[-2] == '> ' + T['topics'][3] and m[-1] == T['branch'] and len(await chips()) == 3, (m[-2:], await chips()))
            await chip((await chips())[0])
            check(f'{l}: then the name', (await log())[-1].startswith(T['name']) and await pg.get_attribute('#chatInput', 'autocomplete') == 'name')
        check('the chat window is a labelled dialog with a live message area', await pg.get_attribute('#chatBox', 'role') == 'dialog' and await pg.get_attribute('#chatLog', 'aria-live') == 'polite')
        direct = await pg.get_attribute('.chat-direct', 'href')
        check('a direct WhatsApp link stays inside the chat', direct.startswith('https://wa.me/994') and await pg.locator('.wa-float').count() == 0, direct)

        # 2. весь разговор на русском
        await go('/ru'); await pg.evaluate('localStorage.removeItem("optika-customer")'); await go('/ru')
        n0 = int(sql('SELECT COUNT(*) FROM ao_orders'))
        await pg.locator('#chatFab').click(); await pg.wait_for_timeout(200)
        check('desktop: the text field is ready for typing', await pg.evaluate("document.activeElement.id") == 'chatInput')
        await chip('Ремонт очков'); await chip('Asioptik — Центр')
        check('no saved name yet — no hint under the question', await chips() == [], await chips())
        await say('А')
        check('a one-letter name is asked again', (await log())[-2:] == ['> А', 'Укажите имя'], (await log())[-2:])
        await say('<img src=x onerror="window.__xss=1">Айдан')
        check('the name is shown as text, never as markup', await pg.locator('#chatLog img').count() == 0 and await pg.evaluate('window.__xss') is None and '<img src=x' in (await log())[-2])
        check('the phone question follows', 'номер телефона' in (await log())[-1] and await pg.get_attribute('#chatInput', 'inputmode') == 'tel' and await pg.get_attribute('#chatInput', 'autocomplete') == 'tel')
        await say('12345')
        check('a short number is asked again', (await log())[-1] == 'Укажите номер телефона полностью', (await log())[-1])
        await say('+994 50 111 22 33 44 55 66 77')
        check('a number with too many digits is asked again', (await log())[-1] == 'В номере лишние цифры, проверьте его', (await log())[-1])
        await say('+994 50 111 22 33')
        check('the last question is optional and can be skipped', await chips() == ['Пропустить'] and 'пропустите' in (await log())[-1], await chips())
        await say('Сломалась дужка')
        rows = await pg.evaluate("[...document.querySelectorAll('.chat-sum div')].map(d => d.querySelector('dt').textContent + ': ' + d.querySelector('dd').textContent)")
        check('summary before sending', rows == ['Тема: Ремонт очков', 'Салон: Asioptik — Центр', 'Имя: <img src=x onerror="window.__xss=1">Айдан', 'Телефон: +994 50 111 22 33', 'Дополнение: Сломалась дужка'], rows)
        check('the field is closed, the send button is shown', await pg.is_disabled('#chatInput') and (await pg.locator('[data-chat-send]').inner_text()).strip() == 'Отправить в WhatsApp')
        check('nothing is sent before the button is pressed', int(sql('SELECT COUNT(*) FROM ao_orders')) == n0 and await opened() == [])
        await pg.locator('[data-chat-send]').click(); await pg.wait_for_timeout(900)
        wa = await opened()
        want = 'Здравствуйте! Пишу с сайта.\n\nУслуга: Ремонт очков\nСалон: Asioptik — Центр\nСломалась дужка\n\n*Клиент:*\nИмя: <img src=x onerror="window.__xss=1">Айдан\nТелефон: +994 50 111 22 33'
        check('WhatsApp opens with the whole request', len(wa) == 1 and wa[0] == 'https://wa.me/994000000000?text=' + want, wa)
        row, data = last_order()
        check('the request is saved for the admin panel', int(sql('SELECT COUNT(*) FROM ao_orders')) == n0 + 1 and row.startswith('message|new|') and row.endswith('|+994 50 111 22 33|ru') and data.get('text') == want
              and data.get('details') == {'topic': 'Ремонт очков', 'branch': 'Asioptik — Центр', 'comment': 'Сломалась дужка'}, row[:300])
        check('thanks, and the button now reopens WhatsApp', (await log())[-1].startswith('Спасибо! Заявку получили') and (await pg.locator('[data-chat-send]').inner_text()).strip() == 'Открыть WhatsApp ещё раз')
        await pg.locator('[data-chat-send]').click(); await pg.wait_for_timeout(700)
        check('pressing again opens WhatsApp, but does not save the request twice', len(await opened()) == 2 and int(sql('SELECT COUNT(*) FROM ao_orders')) == n0 + 1 and len([m for m in await log() if m.startswith('Спасибо')]) == 1)

        # 3. новая заявка: имя и телефон предлагаются подсказкой; свой текст вместо темы; «Любой» салон
        await pg.locator('#chatLog [data-chat-reset]').click(); await pg.wait_for_timeout(150)
        check('«Новая заявка» starts the talk again', len(await log()) == 2 and await chips() == TEXT['ru']['topics'] and not await pg.is_disabled('#chatInput'))
        await say('Есть ли у вас детские оправы?')
        check('own text instead of a topic is accepted', (await log())[-2] == '> Есть ли у вас детские оправы?' and (await log())[-1] == TEXT['ru']['branch'])
        await chip('Любой')
        check('the saved name is offered as a hint', len(await chips()) == 1 and 'Айдан' in (await chips())[0], await chips())
        await say('Лейла')
        check('the saved phone is offered as a hint', await chips() == ['+994 50 111 22 33'], await chips())
        await chip('+994 50 111 22 33'); await chip('Пропустить')
        await pg.locator('[data-chat-send]').click(); await pg.wait_for_timeout(900)
        wa = await opened()
        check('own question goes as «Другой вопрос» with the text; «Любой» adds no shop line',
              wa[-1] == 'https://wa.me/994000000000?text=Здравствуйте! Пишу с сайта.\n\nУслуга: Другой вопрос\nЕсть ли у вас детские оправы?\n\n*Клиент:*\nИмя: Лейла\nТелефон: +994 50 111 22 33', wa[-1])
        d = last_order()[1]
        check('… and is saved the same way', d['details'] == {'topic': 'Другой вопрос', 'branch': '', 'comment': 'Есть ли у вас детские оправы?'} or d['details'] == {'topic': 'Другой вопрос', 'comment': 'Есть ли у вас детские оправы?'}, d['details'])
        # салон, набранный словами
        await pg.locator('.chat-head [data-chat-reset]').click(); await pg.wait_for_timeout(150)
        await chip('Проверка зрения'); await say('asioptik — гянджлик')
        await chip('Лейла'); await chip('+994 50 111 22 33'); await say('После 18:00')
        rows = await pg.evaluate("[...document.querySelectorAll('.chat-sum dd')].map(d => d.textContent)")
        check('a shop typed by name is recognised; the round arrow restarts too', rows == ['Проверка зрения', 'Asioptik — Гянджлик', 'Лейла', '+994 50 111 22 33', 'После 18:00'], rows)

        # 4. смена языка посреди разговора, Escape, меню
        await pg.locator('.hdr-right [data-set-lang="az"]').click(); await pg.wait_for_timeout(300)
        m = await log()
        check('language switch: questions follow the language, answers stay as typed', m[0].startswith(TEXT['az']['hello']) and m[1] == TEXT['az']['q'] and '> Проверка зрения' in m and '> После 18:00' in m
              and (await pg.locator('[data-chat-send]').inner_text()).strip() == TEXT['az']['send'], m[:3])
        await pg.locator('.chat-head [data-chat-close]').focus(); await pg.keyboard.press('Escape'); await pg.wait_for_timeout(150)
        check('Escape closes the chat and returns to the button', await pg.locator('#chatBox').is_hidden() and await pg.evaluate('document.activeElement.id') == 'chatFab' and await pg.get_attribute('#chatFab', 'aria-expanded') == 'false')
        await pg.locator('#chatFab').click(); await pg.wait_for_timeout(150)
        check('reopening keeps the talk where it was', len(await log()) == len(m) and await pg.locator('.chat-sum').is_visible())
        await pg.locator('#chatFab').click(); await pg.wait_for_timeout(150)
        check('the corner button closes the chat too', await pg.locator('#chatBox').is_hidden())
        await pg.context.close()

        # 5. один салон — вопроса о салоне нет
        sql("UPDATE ao_items SET active = 0 WHERE type = 'branch' AND slug <> 'merkez'")
        for f in (ROOT / 'site/storage/cache').glob('*.json'): f.unlink()
        pg = await new_page()
        await go('/ru'); await pg.locator('#chatFab').click(); await pg.wait_for_timeout(200)
        await chip('Контактные линзы')
        check('one shop: the chat goes straight to the name', (await log())[-1].startswith(TEXT['ru']['name']), (await log())[-1])
        await say('Нигяр'); await say('0501112233'); await chip('Пропустить')
        await pg.locator('[data-chat-send]').click(); await pg.wait_for_timeout(700)
        check('one shop: no shop line in the message', (await opened())[-1].endswith('Услуга: Контактные линзы\n\n*Клиент:*\nИмя: Нигяр\nТелефон: 0501112233'), (await opened())[-1])
        await pg.context.close()

        # 6. телефон
        pg = await new_page(390, 844, is_mobile=True, has_touch=True, device_scale_factor=2)
        await go('/ru'); await pg.locator('#chatFab').click(); await pg.wait_for_timeout(250)
        box = await pg.evaluate("(() => { const r = document.getElementById('chatBox').getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom, innerWidth, innerHeight, document.documentElement.scrollWidth - document.documentElement.clientWidth] })()")
        check('phone: the chat fits the screen', box[0] >= 0 and box[1] >= 0 and box[2] <= box[4] and box[3] <= box[5] and box[6] <= 1, box)
        check('phone: the keyboard is not raised until the visitor taps the field', await pg.evaluate('document.activeElement.id') != 'chatInput')
        check('phone: chips are big enough to tap', await pg.evaluate("Math.min(...[...document.querySelectorAll('.chat-chip')].map(c => c.getBoundingClientRect().height))") >= 40)
        await pg.locator('#chatFab').click(); await pg.wait_for_timeout(150)
        await pg.locator('.hdr-right .js-menu-toggle').click(); await pg.wait_for_timeout(350)
        check('phone: the button hides while the site menu is open', await pg.locator('#chatFab').is_hidden())
        await pg.context.close()

        # 7. версия сайта одним файлом: чат есть, заявка уходит в WhatsApp (сервера у неё нет)
        pg = await new_page()
        await pg.goto(ONE + '?lang=ru'); await pg.wait_for_function('window.Shop'); await pg.wait_for_timeout(300)
        await pg.locator('#chatFab').click(); await pg.wait_for_timeout(200)
        await chip('Подбор очков')
        if await chips() and (await log())[-1] == TEXT['ru']['branch']: await chip((await chips())[0])
        await say('Тест'); await say('0501112233'); await chip('Пропустить')
        await pg.locator('[data-chat-send]').click(); await pg.wait_for_timeout(500)
        wa = await opened()
        check('one-file site: the chat works and opens WhatsApp', len(wa) == 1 and 'Услуга: Подбор очков' in wa[0] and 'Имя: Тест' in wa[0], wa)
        await pg.context.close()
        check('no script errors in the browser', not errors, errors[:3])
        await b.close()

    # 8. админ-панель: заявка из чата в «Заказах», тексты чата редактируются на странице «Главная»
    from php_client import admin_client
    a = admin_client()
    s, h, t = a.get('/admin/?p=orders')
    check('admin: chat requests are in «Заказы»', s == 200 and 'Нигяр' in t and 'Лейла' in t)
    s, h, t = a.get('/admin/?p=page&id=home')
    check('admin: chat texts can be edited on the «Главная» page', s == 200 and 'Чат-заявка (кнопка в углу сайта)' in t and 'Что вас интересует?' in t, s)
    print(f'\n{total - len(fails)} of {total} checks passed')
    if fails:
        print('FAILED:', len(fails)); sys.exit(1)

asyncio.run(main())
