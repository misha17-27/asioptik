import asyncio, sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from run import setup, BASE
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        pg = await (await b.new_context()).new_page(); await setup(pg)
        await pg.goto(f'{BASE}/dist/optika-4-lupa.html'); await pg.wait_for_timeout(800)
        inp = pg.locator('#repairForm input[name=phone]')
        for typed, clear in (('501234567', False), ('0501234567', True), ('050 123 45 67', True), ('+994 050 123 45 67', True), ('+994 +994 55 765 43 21', True), ('+7 912 345 67 89', True), ('12345', True)):
            await inp.fill('')
            await inp.focus()
            if clear: await inp.fill('')
            await inp.type(typed)
            await pg.locator('#rpDesc').focus()
            print(repr(typed), '->', repr(await inp.input_value()))
        await b.close()
asyncio.run(main())
