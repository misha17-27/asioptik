"""Снимок страницы: shot.py <путь на локальном сервере> <файл снимка> <ширина> <высота> [масштаб]"""
import asyncio
import sys
from playwright.async_api import async_playwright


async def main(path, out, w, h, scale):
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        pg = await (await b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=scale)).new_page()
        await pg.goto('http://127.0.0.1:8765/' + path)
        await pg.wait_for_timeout(500)
        await pg.screenshot(path=out)
        await b.close()

asyncio.run(main(sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5]) if len(sys.argv) > 5 else 1))
