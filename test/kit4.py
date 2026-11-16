import asyncio, sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from run import setup, BASE, ROOT
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        pg = await (await b.new_context(viewport={'width': 1440, 'height': 900}, device_scale_factor=2)).new_page(); await setup(pg)
        await pg.goto(f'{BASE}/dist/optika-4-lupa.html'); await pg.wait_for_timeout(1000)
        await pg.mouse.move(5, 5)
        clip = await pg.locator('#heroKit .kit').bounding_box()
        clip = {'x': clip['x'], 'y': clip['y'], 'width': clip['width'] * 0.55, 'height': clip['height'] * 0.62}
        await pg.screenshot(path=f'{ROOT}/shots/kit-a.png', clip=clip)
        await pg.evaluate("""() => {
          const svg = document.querySelector('#heroKit .kit');
          svg.querySelectorAll('#kitGlow stop')[0].setAttribute('stop-opacity', '.6');
          svg.querySelectorAll('circle[fill="url(#opt-glass)"]').forEach(c => {
            c.setAttribute('opacity', '.62');
            const ring = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            ring.setAttribute('cx', c.getAttribute('cx')); ring.setAttribute('cy', c.getAttribute('cy')); ring.setAttribute('r', '30');
            ring.setAttribute('fill', 'none'); ring.setAttribute('stroke', 'rgba(24,33,58,.10)'); ring.setAttribute('stroke-width', '3');
            c.parentNode.insertBefore(ring, c.nextSibling.nextSibling.nextSibling);
          });
          svg.querySelectorAll('circle[fill="url(#opt-sheen)"]').forEach(c => c.setAttribute('opacity', '.9'));
        }""")
        await pg.screenshot(path=f'{ROOT}/shots/kit-b.png', clip=clip)
        await b.close()
asyncio.run(main())
