/* ======================================================================
   Логика сайта: каталог, корзина, оформление заказа и отправка в WhatsApp.
   Обычно здесь ничего менять не нужно — товары и контакты задаются
   в блоке «НАСТРОЙКИ МАГАЗИНА» в начале файла.
   ====================================================================== */
(function () {
  'use strict';

  const TH = (typeof THEME !== 'undefined' && THEME) || {};
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.prototype.slice.call((r || document).querySelectorAll(s));
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const cssEsc = s => (window.CSS && CSS.escape ? CSS.escape(String(s)) : String(s).replace(/["\\]/g, '\\$&'));
  const reduced = () => !!(window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches);
  const NB = '\u00A0';
  const p2 = n => String(n).padStart(2, '0');

  /* ---------- форматирование ---------- */
  function money(n) {
    const v = Math.round((+n || 0) * 100) / 100;
    return v.toLocaleString('ru-RU', { minimumFractionDigits: v % 1 ? 2 : 0, maximumFractionDigits: 2 }) + NB + CONFIG.currency;
  }
  function plural(n, f) {
    const a = Math.abs(n) % 100, b = a % 10;
    return f[a > 10 && a < 20 ? 2 : b > 1 && b < 5 ? 1 : b === 1 ? 0 : 2];
  }
  function nowStr() {
    const d = new Date();
    return `${p2(d.getDate())}.${p2(d.getMonth() + 1)}.${d.getFullYear()}, ${p2(d.getHours())}:${p2(d.getMinutes())}`;
  }
  function makeId(prefix) {
    const d = new Date();
    return `${prefix}-${p2(d.getDate())}${p2(d.getMonth() + 1)}-${Math.floor(1000 + Math.random() * 9000)}`;
  }
  const digitsCount = s => String(s || '').replace(/\D/g, '').length;

  /* ---------- хранилище браузера ---------- */
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* хранилище недоступно */ } },
  };
  const CART_KEY = 'optika-cart';
  const CUSTOMER_KEY = 'optika-customer';

  /* ---------- товары и параметры ---------- */
  const byId = {};
  PRODUCTS.forEach(p => { byId[p.id] = p; });
  const catById = {};
  CATEGORIES.forEach(c => { catById[c.id] = c; });
  const catName = id => (catById[id] ? catById[id].name : '');

  function normVal(x) { return x && typeof x === 'object' ? { v: String(x.v), d: +x.d || 0 } : { v: String(x), d: 0 }; }

  function defsOf(p) {
    if (p._defs) return p._defs;
    const out = [];
    if (p.colors && p.colors.length) {
      out.push({
        k: 'color', label: p.colorLabel || 'Цвет', type: 'swatch', required: true, def: p.colors[0].n,
        values: p.colors.map(c => ({ v: c.n, d: +c.d || 0, color: c })),
      });
    }
    (p.opts || []).forEach(o => {
      const groups = o.groups ? o.groups.map(g => ({ label: g.label, values: g.values.map(normVal) })) : null;
      const values = groups ? [].concat.apply([], groups.map(g => g.values)) : (o.values || []).map(normVal);
      let def = '';
      if (o.default != null) def = String(o.default);
      else if ((o.preselect || values.length === 1) && values.length) def = values[0].v;
      out.push({ k: o.k, label: o.label, short: o.short, hint: o.hint, type: 'select', groups, values, required: o.required !== false, def });
    });
    Object.defineProperty(p, '_defs', { value: out, enumerable: false });
    return out;
  }
  const needsOptions = p => !!(p.opts && p.opts.length);
  function colorOf(p, sel) {
    if (!p.colors || !p.colors.length) return null;
    if (typeof sel === 'number') return p.colors[sel] || p.colors[0];
    if (sel) { const f = p.colors.find(c => c.n === sel); if (f) return f; }
    return p.colors[0];
  }
  function deltaOf(p, sel) {
    let s = 0;
    defsOf(p).forEach(d => { const v = d.values.find(x => x.v === sel[d.k]); if (v) s += v.d; });
    return s;
  }
  const unitPrice = (p, sel) => p.price + deltaOf(p, sel);
  const hasDeltas = p => defsOf(p).some(d => d.values.some(v => v.d > 0));
  const priceLabel = p => (hasDeltas(p) ? 'от ' : '') + money(p.price);
  const optsText = (p, sel) => defsOf(p).filter(d => sel[d.k]).map(d => (d.short ? d.short + ' ' : '') + sel[d.k]).join(', ');
  const optsLong = (p, sel) => defsOf(p).filter(d => sel[d.k]).map(d => (d.short || d.label) + ': ' + sel[d.k]).join(', ');
  const keyOf = (id, sel) => id + '|' + defsOf(byId[id]).map(d => sel[d.k] || '').join('|');
  function badges(p) {
    const out = [];
    if (p.badge) out.push({ t: p.badge });
    if (p.old && p.old > p.price) out.push({ t: '−' + Math.round((1 - p.price / p.old) * 100) + '%', sale: true });
    return out;
  }

  /* ---------- иконки ---------- */
  const ic = d => `<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${d}</svg>`;
  const ICON = {
    bag: ic('<path d="M5 8h14l-1.2 11.2a2 2 0 0 1-2 1.8H8.2a2 2 0 0 1-2-1.8L5 8Z"/><path d="M9 8V6.5a3 3 0 0 1 6 0V8"/>'),
    x: ic('<path d="M6 6l12 12M18 6 6 18"/>'),
    menu: ic('<path d="M4 7h16M4 12h16M4 17h16"/>'),
    chat: ic('<path d="M5 4.5h14a2 2 0 0 1 2 2V15a2 2 0 0 1-2 2h-7.5L7 20.5V17H5a2 2 0 0 1-2-2V6.5a2 2 0 0 1 2-2Z"/><path d="M8.3 10.8h.01M12 10.8h.01M15.7 10.8h.01" stroke-width="2.6"/>'),
    phone: ic('<path d="M6.5 3.5h2.8l1.6 4.4-2 1.4a11.5 11.5 0 0 0 5.8 5.8l1.4-2 4.4 1.6v2.8a2 2 0 0 1-2.1 2A16.5 16.5 0 0 1 4.5 5.6a2 2 0 0 1 2-2.1Z"/>'),
    pin: ic('<path d="M12 21s-6.5-5.8-6.5-11a6.5 6.5 0 0 1 13 0c0 5.2-6.5 11-6.5 11Z"/><circle cx="12" cy="10" r="2.3"/>'),
    clock: ic('<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>'),
    search: ic('<circle cx="11" cy="11" r="6.5"/><path d="m20 20-4.2-4.2"/>'),
    at: ic('<circle cx="12" cy="12" r="3.6"/><path d="M15.6 8.4v4.6a2.4 2.4 0 0 0 4.8 0V12a8.4 8.4 0 1 0-3.3 6.7"/>'),
    check: ic('<path d="m5 12.5 4.5 4.5L19 7.5"/>'),
    tool: ic('<path d="M14.6 6.4a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.1-3.1a5.6 5.6 0 0 1-7.4 7.4l-6.4 6.4a2 2 0 0 1-2.9-2.9l6.4-6.4a5.6 5.6 0 0 1 7.4-7.4l-3.2 3Z"/>'),
    truck: ic('<path d="M3 6.5h11V16H3zM14 9.5h3.8L21 13v3h-7"/><circle cx="7" cy="17.5" r="1.7"/><circle cx="17" cy="17.5" r="1.7"/>'),
    eye: ic('<path d="M2.5 12s3.5-6.5 9.5-6.5 9.5 6.5 9.5 6.5-3.5 6.5-9.5 6.5S2.5 12 2.5 12Z"/><circle cx="12" cy="12" r="2.8"/>'),
    minus: ic('<path d="M6 12h12"/>'),
    plus: ic('<path d="M12 6v12M6 12h12"/>'),
  };

  /* ---------- иллюстрации товаров ---------- */
  const svgOpen = () => '<svg class="art" viewBox="0 0 240 120" aria-hidden="true" focusable="false">';

  // Форма одной (левой) линзы; правая — зеркальная копия.
  // b — точка крепления переносицы, h — шарнир заушника, bar — верхний мостик авиаторов
  const SHAPES = {
    round:    { d: 'M-30,0a30,30 0 1,0 60,0a30,30 0 1,0 -60,0Z', b: [28.2, -10.3], h: [-28.5, -9.5] },
    oval:     { d: 'M-34,0a34,25 0 1,0 68,0a34,25 0 1,0 -68,0Z', b: [32.2, -8], h: [-32.5, -7.5] },
    rect:     { d: 'M-25,-22H25Q35,-22 35,-12V12Q35,22 25,22H-25Q-35,22 -35,12V-12Q-35,-22 -25,-22Z', b: [35, -9], h: [-35, -13] },
    square:   { d: 'M-18,-29H18Q34,-29 34,-13V13Q34,29 18,29H-18Q-34,29 -34,13V-13Q-34,-29 -18,-29Z', b: [34, -10], h: [-34, -15] },
    cateye:   { d: 'M-42,-24C-20,-24 12,-20 30,-14C36,-6 34,10 22,18C8,26 -20,24 -32,12C-40,2 -42,-12 -42,-24Z', b: [31.5, -11], h: [-41, -22] },
    aviator:  { d: 'M30,-19C12,-22 -22,-23 -36,-15C-44,-8 -40,10 -28,20C-14,31 8,32 20,20C28,11 32,-2 32,-12C32,-16 31,-18 30,-19Z', b: [31.5, -14], h: [-38, -12], bar: [16, -21.5] },
    hex:      { d: 'M-18,-26H18L34,0L18,26H-18L-34,0Z', b: [29, -8], h: [-27, -12] },
    trapeze:  { d: 'M-38,-23H33Q38,-23 37,-16L32,12Q30,21 20,21H-20Q-30,21 -32,13L-38,-15Q-40,-23 -38,-23Z', b: [35.5, -11], h: [-39, -19] },
    browline: { d: 'M-34,-16Q-34,-22 -26,-22H26Q34,-22 34,-16V2Q34,24 4,24H-6Q-34,24 -34,2Z', b: [34, -12], h: [-35, -17], brow: 'M-37,-16Q-37,-24 -28,-24H28Q37,-24 37,-16' },
  };

  function glasses(o) {
    const S = SHAPES[o.shape] || SHAPES.round;
    const L = 76, R = 164, Y = 60;
    const brow = !!S.brow;
    const sw = o.sw || (o.metal ? 2.6 : 6.5);
    const paint = o.c === 'tortoise' ? 'url(#opt-tortoise)' : (o.c || '#222');
    const metalPaint = o.c2 || '#9fa4ab';
    const tL = `translate(${L} ${Y})`, tR = `translate(${R} ${Y}) scale(-1 1)`;
    const lens = `<path d="${S.d}" transform="${tL}"/><path d="${S.d}" transform="${tR}"/>`;
    const bx1 = L + S.b[0], bx2 = R - S.b[0], by = Y + S.b[1];
    const hx1 = L + S.h[0], hx2 = R - S.h[0], hy = Y + S.h[1];
    const bridge = `<path d="M${bx1} ${by}Q120 ${by - 9} ${bx2} ${by}"/>`;
    const temples = `<path d="M${hx1} ${hy}l-15 -3.5M${hx2} ${hy}l15 -3.5"/>`;
    const bar = S.bar ? `<path d="M${L + S.bar[0]} ${Y + S.bar[1]}H${R - S.bar[0]}"/>` : '';
    const browPath = brow ? `<path d="${S.brow}" transform="${tL}"/><path d="${S.brow}" transform="${tR}"/>` : '';
    let s = svgOpen();
    s += `<ellipse cx="120" cy="108" rx="80" ry="4.5" fill="#000" opacity="${o.shadow != null ? o.shadow : 0.07}"/>`;
    if (o.sun) {
      s += `<g fill="${o.l || '#2b2b30'}" fill-opacity=".9">${lens}</g>`;
      if (o.grad) s += `<g fill="url(#opt-fade)">${lens}</g>`;
      s += `<g fill="url(#opt-glare)">${lens}</g>`;
    } else {
      s += `<g fill="${o.glass || 'url(#opt-glass)'}">${lens}</g>`;
    }
    s += `<path d="M${L - 17} ${Y - 4}l9 -10M${R - 17} ${Y - 4}l9 -10" stroke="#fff" stroke-opacity="${o.sun ? 0.32 : 0.8}" stroke-width="2.6" stroke-linecap="round" fill="none"/>`;
    if (o.rim) {
      s += `<g fill="none" stroke="${o.rim}" stroke-width="${(brow ? 8 : sw) + 2.2}" stroke-linejoin="round" stroke-linecap="round">${brow ? browPath + lens : lens}${bridge}${bar}${temples}</g>`;
    }
    const op = o.a != null ? ` opacity="${o.a}"` : '';
    if (brow) {
      s += `<g fill="none" stroke="${metalPaint}" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round">${lens}${bridge}</g>`;
      s += `<g fill="none" stroke="${paint}" stroke-width="8" stroke-linejoin="round" stroke-linecap="round"${op}>${browPath}${temples}</g>`;
    } else {
      s += `<g fill="none" stroke="${paint}" stroke-width="${sw}" stroke-linejoin="round" stroke-linecap="round"${op}>${lens}${bridge}${bar}${temples}</g>`;
    }
    if (o.metal || brow) {
      s += `<g fill="${o.pad || 'rgba(255,255,255,.8)'}" stroke="rgba(0,0,0,.25)" stroke-width=".8"><ellipse cx="${bx1 - 6}" cy="${Y + 9}" rx="2.6" ry="5"/><ellipse cx="${bx2 + 6}" cy="${Y + 9}" rx="2.6" ry="5"/></g>`;
    }
    return s + '</svg>';
  }

  function cbox(p) {
    const c = p.tone || '#2a9fc4';
    return svgOpen() +
      '<ellipse cx="128" cy="108" rx="60" ry="5" fill="#000" opacity=".08"/>' +
      `<path d="M74 28 88 19h94l-14 9Z" fill="${c}" opacity=".45"/>` +
      `<path d="M168 28l14-9v76l-14 9Z" fill="${c}" opacity=".7"/>` +
      '<rect x="74" y="28" width="94" height="76" rx="3" fill="#fff"/>' +
      `<path d="M74 31a3 3 0 0 1 3-3h88a3 3 0 0 1 3 3v24H74Z" fill="${c}"/>` +
      '<rect x="84" y="37" width="40" height="5" rx="2.5" fill="#fff"/>' +
      '<rect x="84" y="46" width="24" height="3.5" rx="1.75" fill="#fff" opacity=".7"/>' +
      '<circle cx="151" cy="41.5" r="8" fill="none" stroke="#fff" stroke-width="2"/>' +
      '<path d="M146.5 40q4.5-4 9 0" fill="none" stroke="#fff" stroke-width="1.6" stroke-linecap="round" opacity=".85"/>' +
      `<text x="84" y="84" font-size="23" font-weight="700" fill="${c}">${esc(p.pack || '')}</text>` +
      '<rect x="118" y="70" width="38" height="3.5" rx="1.75" fill="#1c2430" opacity=".16"/>' +
      '<rect x="118" y="78" width="28" height="3.5" rx="1.75" fill="#1c2430" opacity=".1"/>' +
      `<rect x="84" y="93" width="72" height="2.5" rx="1.25" fill="${c}" opacity=".35"/>` +
      '<rect x="74.5" y="28.5" width="93" height="75" rx="3" fill="none" stroke="#1c2430" stroke-opacity=".1"/>' +
      '</svg>';
  }

  const glassFill = () => (TH.art && TH.art.glass) || 'url(#opt-glass)';
  function iris(p, col) {
    const c = (col && col.c) || '#5f9fd6';
    let fib = '';
    for (let i = 0; i < 30; i++) {
      const a = (i / 30) * Math.PI * 2, r1 = 11, r2 = i % 2 ? 22 : 24.5;
      fib += `M${(Math.cos(a) * r1).toFixed(1)} ${(Math.sin(a) * r1).toFixed(1)}L${(Math.cos(a) * r2).toFixed(1)} ${(Math.sin(a) * r2).toFixed(1)}`;
    }
    const lens = (x, y, s) => `<g transform="translate(${x} ${y}) scale(${s})">` +
      `<circle r="34" fill="${glassFill()}"/>` +
      `<circle r="25.5" fill="${c}"/>` +
      `<path d="${fib}" stroke="#fff" stroke-opacity=".38" stroke-width="1.3" fill="none"/>` +
      '<circle r="25.5" fill="none" stroke="#14181f" stroke-opacity=".3" stroke-width="2.6"/>' +
      '<circle r="9.5" fill="#14181f" fill-opacity=".85"/>' +
      '<circle r="34" fill="none" stroke="#7f8c95" stroke-opacity=".4" stroke-width="1.2"/>' +
      '<path d="M-22 -14q9-13 26-12" fill="none" stroke="#fff" stroke-opacity=".8" stroke-width="3" stroke-linecap="round"/>' +
      '</g>';
    return svgOpen() + '<ellipse cx="124" cy="108" rx="66" ry="4.5" fill="#000" opacity=".07"/>' + lens(152, 64, 0.84) + lens(98, 58, 1) + '</svg>';
  }

  function slens(p, col) {
    const k = p.kind || 'ar';
    const refl = k === 'blue' ? '#7b84ff' : '#3fcf8e';
    const disc = (x, y, tint) => `<g transform="translate(${x} ${y})">` +
      `<circle r="36" fill="${tint || glassFill()}"${tint ? ' fill-opacity=".88"' : ''}/>` +
      '<circle r="36" fill="url(#opt-glare)"/>' +
      (k === 'prog' ? '<path d="M-5 -6c-2 12 1 22-3 34M5 -6c2 12-1 22 3 34" fill="none" stroke="#7f8c95" stroke-opacity=".6" stroke-width="1.2" stroke-dasharray="2 3"/><path d="M-30 -8h60" stroke="#7f8c95" stroke-opacity=".35" stroke-width="1" stroke-dasharray="2 3"/>' : '') +
      `<path d="M-27 -16a31 31 0 0 1 22-17" fill="none" stroke="${refl}" stroke-opacity=".8" stroke-width="4" stroke-linecap="round"/>` +
      '<circle r="36" fill="none" stroke="#7f8c95" stroke-opacity=".5" stroke-width="1.3"/>' +
      '<circle r="33.5" fill="none" stroke="#fff" stroke-opacity=".55" stroke-width="1"/>' +
      '</g>';
    const dark = k === 'photo' ? ((col && col.c) || '#4a4f57') : null;
    return svgOpen() + '<ellipse cx="122" cy="108" rx="70" ry="4.5" fill="#000" opacity=".07"/>' + disc(146, 62, dark) + disc(98, 58, null) + '</svg>';
  }

  function bottle(p) {
    const c = p.tone || '#2a9fc4';
    const body = 'M104 26h32c8 3 11 9 11 17v59a8 8 0 0 1-8 8H101a8 8 0 0 1-8-8V43c0-8 3-14 11-17Z';
    return svgOpen() + '<ellipse cx="120" cy="113" rx="32" ry="4" fill="#000" opacity=".08"/>' +
      `<rect x="109" y="5" width="22" height="15" rx="3" fill="${c}"/>` +
      `<rect x="106" y="18" width="28" height="8" rx="2" fill="${c}" opacity=".78"/>` +
      `<path d="${body}" fill="#fff"/>` +
      `<path d="M93 54h54v34H93Z" fill="${c}"/>` +
      '<rect x="101" y="62" width="26" height="4" rx="2" fill="#fff"/>' +
      '<rect x="101" y="70" width="17" height="3" rx="1.5" fill="#fff" opacity=".7"/>' +
      '<path d="M100 34v66" stroke="#fff" stroke-width="3" stroke-linecap="round" opacity=".55"/>' +
      `<path d="${body}" fill="none" stroke="#1c2430" stroke-opacity=".12"/>` +
      '</svg>';
  }

  function drops(p) {
    const c = p.tone || '#23a174';
    return svgOpen() + '<ellipse cx="120" cy="113" rx="24" ry="3.5" fill="#000" opacity=".08"/>' +
      '<path d="M114 22l6-15 6 15Z" fill="#fff" stroke="#1c2430" stroke-opacity=".15"/>' +
      `<rect x="109" y="20" width="22" height="24" rx="4" fill="${c}"/>` +
      '<rect x="104" y="42" width="32" height="68" rx="9" fill="#fff"/>' +
      `<rect x="104" y="58" width="32" height="30" fill="${c}" opacity=".9"/>` +
      '<rect x="110" y="65" width="16" height="3.5" rx="1.75" fill="#fff"/>' +
      '<path d="M110 50v54" stroke="#fff" stroke-width="2.6" stroke-linecap="round" opacity=".55"/>' +
      '<rect x="104" y="42" width="32" height="68" rx="9" fill="none" stroke="#1c2430" stroke-opacity=".12"/>' +
      '</svg>';
  }

  function lenscase(p) {
    const c = p.tone || '#3a86d4';
    return svgOpen() + '<ellipse cx="120" cy="96" rx="70" ry="4.5" fill="#000" opacity=".08"/>' +
      `<rect x="88" y="52" width="64" height="18" rx="6" fill="${c}" opacity=".8"/>` +
      `<circle cx="84" cy="61" r="27" fill="${c}"/><circle cx="84" cy="61" r="19" fill="#fff" opacity=".92"/>` +
      `<circle cx="156" cy="61" r="27" fill="#fff"/><circle cx="156" cy="61" r="24" fill="none" stroke="${c}" stroke-width="6"/><circle cx="156" cy="61" r="19" fill="${c}" opacity=".14"/>` +
      `<text x="84" y="68" text-anchor="middle" font-size="19" font-weight="700" fill="${c}">L</text>` +
      `<text x="156" y="68" text-anchor="middle" font-size="19" font-weight="700" fill="${c}">R</text>` +
      '</svg>';
  }

  function glassCase(p, col) {
    const c = (col && col.c) || p.tone || '#3d4048';
    return svgOpen() + '<ellipse cx="120" cy="100" rx="84" ry="5" fill="#000" opacity=".09"/>' +
      `<rect x="36" y="34" width="168" height="58" rx="29" fill="${c}"/>` +
      '<path d="M40 63h160" stroke="#000" stroke-opacity=".22" stroke-width="1.5"/>' +
      '<path d="M58 42q62-12 124 0" fill="none" stroke="#fff" stroke-opacity=".28" stroke-width="3" stroke-linecap="round"/>' +
      '<rect x="110" y="59" width="20" height="8" rx="4" fill="#fff" opacity=".4"/>' +
      '</svg>';
  }

  function cloth(p) {
    const c = p.tone || '#8e7cc3';
    return svgOpen() + '<ellipse cx="120" cy="104" rx="64" ry="4.5" fill="#000" opacity=".08"/>' +
      `<path d="M74 24h92l8 76H66Z" fill="${c}"/>` +
      '<path d="M120 24l2 76M70 62h100" stroke="#fff" stroke-opacity=".28" stroke-width="1.5"/>' +
      '<path d="M140 86h22" stroke="#fff" stroke-opacity=".6" stroke-width="2" stroke-linecap="round"/>' +
      '<path d="M74 24h92l8 76H66Z" fill="none" stroke="#000" stroke-opacity=".08"/>' +
      '</svg>';
  }

  function art(p, sel) {
    const col = colorOf(p, sel);
    const img = (col && col.img) || p.img;
    if (img) return `<img class="art-img" src="${esc(img)}" alt="" loading="lazy">`;
    const A = TH.art || {};
    switch (p.art) {
      case 'glasses':
        return glasses({
          shape: p.shape, c: col ? col.c : '#222', a: col ? col.a : null, c2: col ? col.c2 : null, l: col ? col.l : null,
          metal: p.metal, sun: p.sun, grad: p.grad, sw: p.sw, rim: A.rim, glass: A.glass, pad: A.pad,
        });
      case 'cbox': return cbox(p);
      case 'iris': return iris(p, col);
      case 'slens': return slens(p, col);
      case 'bottle': return bottle(p);
      case 'drops': return drops(p);
      case 'lenscase': return lenscase(p);
      case 'case': return glassCase(p, col);
      case 'cloth': return cloth(p);
      default: return svgOpen() + '</svg>';
    }
  }

  function hexA(h, a) {
    const m = /^#?([\da-f]{2})([\da-f]{2})([\da-f]{2})$/i.exec(h);
    return m ? `rgba(${parseInt(m[1], 16)},${parseInt(m[2], 16)},${parseInt(m[3], 16)},${a})` : h;
  }
  function swAttr(c) {
    if (!c) return '';
    if (c.c === 'tortoise') return 'data-tortoise';
    const base = c.a != null && c.a < 1 ? hexA(c.c, c.a) : c.c;
    let bg = base;
    if (c.c2) bg = `linear-gradient(135deg, ${base} 0 55%, ${c.c2} 55% 100%)`;
    else if (c.l) bg = `radial-gradient(circle, ${c.l} 0 44%, ${base} 46%)`;
    return `style="--c:${esc(bg)}"`;
  }
  function swatches(p) {
    if (!p.colors || p.colors.length < 2) return '';
    const cur = state.sel[p.id] || 0;
    return '<div class="swatches" role="group" aria-label="Цвет">' + p.colors.map((c, i) =>
      `<button type="button" class="sw${i === cur ? ' is-active' : ''}" data-swatch="${i}" aria-pressed="${i === cur}" aria-label="${esc(c.n)}" title="${esc(c.n)}" ${swAttr(c)}></button>`
    ).join('') + '</div>';
  }

  function injectDefs() {
    const d = document.createElement('div');
    d.setAttribute('aria-hidden', 'true');
    d.style.cssText = 'position:absolute;width:0;height:0;overflow:hidden';
    d.innerHTML = '<svg width="0" height="0" focusable="false"><defs>' +
      '<linearGradient id="opt-glass" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".95"/><stop offset=".55" stop-color="#e4edf1" stop-opacity=".55"/><stop offset="1" stop-color="#d3dfe6" stop-opacity=".5"/></linearGradient>' +
      '<linearGradient id="opt-sheen" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#8ee6c8" stop-opacity=".32"/><stop offset=".5" stop-color="#5b6a9a" stop-opacity=".06"/><stop offset="1" stop-color="#9c8bff" stop-opacity=".34"/></linearGradient>' +
      '<linearGradient id="opt-glare" x1="0" y1="0" x2=".7" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".42"/><stop offset=".45" stop-color="#fff" stop-opacity="0"/></linearGradient>' +
      '<linearGradient id="opt-fade" x1="0" y1="0" x2="0" y2="1"><stop offset=".25" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff" stop-opacity=".6"/></linearGradient>' +
      '<filter id="opt-tt" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">' +
        '<feTurbulence type="fractalNoise" baseFrequency="0.045 0.075" numOctaves="3" seed="8" stitchTiles="stitch" result="n"/>' +
        '<feColorMatrix in="n" type="matrix" values="0 0 0 0 .17  0 0 0 0 .085  0 0 0 0 .03  4.2 0 0 0 -2.05" result="dk"/>' +
        '<feColorMatrix in="n" type="matrix" values="0 0 0 0 .47  0 0 0 0 .23  0 0 0 0 .07  0 3.2 0 0 -1.35" result="md"/>' +
        '<feFlood flood-color="#c98b3a" result="bs"/>' +
        '<feMerge><feMergeNode in="bs"/><feMergeNode in="md"/><feMergeNode in="dk"/></feMerge>' +
      '</filter>' +
      '<pattern id="opt-tortoise" width="120" height="120" patternUnits="userSpaceOnUse"><rect width="120" height="120" filter="url(#opt-tt)"/></pattern>' +
      '</defs></svg>';
    document.body.insertBefore(d, document.body.firstChild);
  }

  /* ---------- состояние ---------- */
  const state = { cat: 'all', q: '', sort: 'default', sel: {}, cart: [], pm: null };

  /* ---------- каталог ---------- */
  const norm = s => String(s || '').toLowerCase().replace(/ё/g, 'е');
  const colorNames = p => (p.colors || []).map(c => c.n).join(' ');
  function filtered() {
    let list = PRODUCTS.filter(p => state.cat === 'all' || p.cat === state.cat);
    if (state.q) {
      const q = norm(state.q);
      list = list.filter(p => norm(p.name + ' ' + (p.sub || '') + ' ' + catName(p.cat) + ' ' + colorNames(p)).indexOf(q) !== -1);
      // если искали по цвету, на карточках сразу показываем этот цвет
      list.forEach(p => {
        if (!p.colors) return;
        const i = p.colors.findIndex(c => norm(c.n).indexOf(q) !== -1);
        if (i >= 0) state.sel[p.id] = i;
      });
    }
    if (state.sort === 'asc') list = list.slice().sort((a, b) => a.price - b.price);
    if (state.sort === 'desc') list = list.slice().sort((a, b) => b.price - a.price);
    return list;
  }

  function renderTabs() {
    const box = $('#catTabs');
    if (!box) return;
    const all = [{ id: 'all', name: 'Все товары', short: 'Все товары' }].concat(CATEGORIES);
    box.innerHTML = all.map(c => {
      const n = c.id === 'all' ? PRODUCTS.length : PRODUCTS.filter(p => p.cat === c.id).length;
      const on = state.cat === c.id;
      return TH.tab ? TH.tab(c, n, on)
        : `<button type="button" class="tab${on ? ' is-active' : ''}" data-cat="${c.id}" aria-pressed="${on}">${esc(c.short || c.name)}<span class="tab-n">${n}</span></button>`;
    }).join('');
  }

  function renderProducts() {
    const grid = $('#productsGrid');
    if (!grid) return;
    const list = filtered();
    grid.innerHTML = list.map(p => (TH.card ? TH.card(p) : `<article data-pid="${p.id}">${esc(p.name)}</article>`)).join('');
    const empty = $('#catalogEmpty');
    if (empty) empty.hidden = list.length > 0;
    const cnt = $('#resultCount');
    if (cnt) cnt.textContent = list.length + ' ' + plural(list.length, ['товар', 'товара', 'товаров']);
    $$('#catTabs [data-cat]').forEach(b => {
      const on = b.dataset.cat === state.cat;
      b.classList.toggle('is-active', on);
      b.setAttribute('aria-pressed', on);
    });
    if (TH.onRender) TH.onRender();
  }

  function onGridClick(e) {
    const card = e.target.closest('[data-pid]');
    if (!card) return;
    const pid = card.dataset.pid, p = byId[pid];
    const sw = e.target.closest('[data-swatch]');
    if (sw) {
      const idx = +sw.dataset.swatch;
      state.sel[pid] = idx;
      updateCardColor(card, p, idx);
      return;
    }
    if (e.target.closest('[data-add]')) { quickAdd(pid); return; }
    if (e.target.closest('[data-view]')) openProduct(pid);
  }
  function updateCardColor(card, p, idx) {
    const a = card.querySelector('.js-art');
    if (a) a.innerHTML = art(p, idx);
    $$('[data-swatch]', card).forEach(b => {
      const on = +b.dataset.swatch === idx;
      b.classList.toggle('is-active', on);
      b.setAttribute('aria-pressed', on);
    });
    const cn = card.querySelector('.js-color-name');
    if (cn && p.colors) cn.textContent = p.colors[idx].n;
    if (TH.onSwatch) TH.onSwatch(card, p, idx);
  }
  function syncCard(pid) {
    const card = $(`#productsGrid [data-pid="${cssEsc(pid)}"]`);
    if (card) updateCardColor(card, byId[pid], state.sel[pid] || 0);
  }

  function quickAdd(pid) {
    const p = byId[pid];
    if (needsOptions(p)) { openProduct(pid); return; }
    const sel = {};
    if (p.colors && p.colors.length) sel.color = p.colors[state.sel[pid] || 0].n;
    addItem(pid, sel, 1);
    toast('Добавлено в корзину: ' + p.name);
  }

  /* ---------- окно товара ---------- */
  function openProduct(pid) {
    const p = byId[pid];
    if (!p) return;
    const sel = {};
    defsOf(p).forEach(d => { if (d.def) sel[d.k] = d.def; });
    if (p.colors && p.colors.length) sel.color = p.colors[state.sel[pid] || 0].n;
    state.pm = { pid, sel, qty: 1 };
    renderPM(true);
    openLayer($('#productModal'));
  }

  function optHTML(d, sel) {
    if (d.type === 'swatch') {
      return `<fieldset class="opt opt-sw"><legend>${esc(d.label)}: <span class="js-sw-current">${esc(sel.color || '')}</span></legend><div class="swatches">` +
        d.values.map(v => `<label class="sw-pick"><input type="radio" name="opt-color" value="${esc(v.v)}"${sel.color === v.v ? ' checked' : ''}><span class="sw" ${swAttr(v.color)} title="${esc(v.v)}"></span><span class="vh">${esc(v.v)}</span></label>`).join('') +
        '</div></fieldset>';
    }
    if (d.values.length === 1) {
      return `<div class="opt opt-fixed"><span class="opt-label">${esc(d.label)}</span><span class="opt-value">${esc(d.values[0].v)}</span></div>`;
    }
    const tag = v => `<option value="${esc(v.v)}"${sel[d.k] === v.v ? ' selected' : ''}>${esc(v.v)}${v.d ? ' (+' + money(v.d) + ')' : ''}</option>`;
    const inner = d.groups
      ? d.groups.map(g => `<optgroup label="${esc(g.label)}">${g.values.map(tag).join('')}</optgroup>`).join('')
      : d.values.map(tag).join('');
    const id = 'opt-' + d.k;
    return `<div class="opt opt-sel"><label class="opt-label" for="${id}">${esc(d.label)}</label>` +
      `<select id="${id}" data-opt="${d.k}">${d.def ? '' : '<option value="">Выберите</option>'}${inner}</select>` +
      (d.hint ? `<p class="opt-hint">${esc(d.hint)}</p>` : '') + '</div>';
  }

  function renderPM(full) {
    const pm = state.pm, p = byId[pm.pid];
    if (full) {
      $('#pmCat').textContent = catName(p.cat);
      $('#pmName').textContent = p.name;
      $('#pmSub').textContent = p.sub || '';
      const info = $('#pmInfo');
      info.innerHTML = (p.info || []).map(r => `<div><dt>${esc(r[0])}</dt><dd>${esc(r[1])}</dd></div>`).join('');
      info.hidden = !(p.info && p.info.length);
      $('#pmOpts').innerHTML = defsOf(p).map(d => optHTML(d, pm.sel)).join('');
      $('#pmError').hidden = true;
    }
    $('#pmArt').innerHTML = art(p, pm.sel.color);
    const u = unitPrice(p, pm.sel);
    $('#pmPrice').textContent = money(u * pm.qty);
    const old = $('#pmOld');
    old.hidden = !p.old;
    old.textContent = p.old ? money((p.old + deltaOf(p, pm.sel)) * pm.qty) : '';
    $('#pmQtyVal').textContent = pm.qty;
    const cur = $('#pmOpts .js-sw-current');
    if (cur) cur.textContent = pm.sel.color || '';
    if (TH.onPM) TH.onPM(p, pm.sel);
  }

  function bindProductModal() {
    const m = $('#productModal');
    $('#pmOpts').addEventListener('change', e => {
      const t = e.target;
      if (!state.pm) return;
      if (t.name === 'opt-color') state.pm.sel.color = t.value;
      else if (t.dataset.opt) {
        if (t.value) state.pm.sel[t.dataset.opt] = t.value; else delete state.pm.sel[t.dataset.opt];
        const box = t.closest('.opt');
        if (box) box.classList.remove('is-invalid');
      }
      $('#pmError').hidden = true;
      renderPM(false);
    });
    m.addEventListener('click', e => {
      const q = e.target.closest('[data-pm-qty]');
      if (!q || !state.pm) return;
      state.pm.qty = Math.min(99, Math.max(1, state.pm.qty + (+q.dataset.pmQty)));
      renderPM(false);
    });
    $('#pmAdd').addEventListener('click', () => {
      const pm = state.pm, p = byId[pm.pid];
      const missing = defsOf(p).filter(d => d.required && !pm.sel[d.k]);
      if (missing.length) {
        const err = $('#pmError');
        err.textContent = 'Выберите: ' + missing.map(d => d.label).join(', ');
        err.hidden = false;
        missing.forEach(d => { const s = $(`#pmOpts [data-opt="${d.k}"]`); if (s) s.closest('.opt').classList.add('is-invalid'); });
        const first = $(`#pmOpts [data-opt="${missing[0].k}"]`);
        if (first) first.focus();
        return;
      }
      if (p.colors && pm.sel.color) {
        const idx = p.colors.findIndex(c => c.n === pm.sel.color);
        if (idx >= 0) { state.sel[p.id] = idx; syncCard(p.id); }
      }
      addItem(p.id, pm.sel, pm.qty);
      closeLayer(m, true);
      toast('Добавлено в корзину: ' + p.name);
    });
  }

  /* ---------- корзина ---------- */
  function loadCart() {
    const raw = store.get(CART_KEY, []);
    state.cart = (Array.isArray(raw) ? raw : [])
      .filter(it => it && byId[it.id] && it.qty > 0)
      .map(it => ({ id: it.id, sel: it.sel || {}, qty: Math.min(99, Math.max(1, it.qty | 0)) }));
  }
  const saveCart = () => store.set(CART_KEY, state.cart);
  function addItem(id, sel, qty) {
    const k = keyOf(id, sel);
    const ex = state.cart.find(it => keyOf(it.id, it.sel) === k);
    if (ex) ex.qty = Math.min(99, ex.qty + qty);
    else state.cart.push({ id, sel: Object.assign({}, sel), qty });
    saveCart();
    renderCart();
    bump();
  }
  function setQty(k, q) {
    const it = state.cart.find(x => keyOf(x.id, x.sel) === k);
    if (!it) return;
    if (q <= 0) state.cart = state.cart.filter(x => x !== it);
    else it.qty = Math.min(99, q);
    saveCart();
    renderCart();
  }
  const cartCount = () => state.cart.reduce((s, it) => s + it.qty, 0);
  const cartSubtotal = () => state.cart.reduce((s, it) => s + unitPrice(byId[it.id], it.sel) * it.qty, 0);
  function deliveryCost(sub, method) {
    if (method !== 'courier') return 0;
    const lim = +CONFIG.freeDeliveryFrom || 0;
    return lim && sub >= lim ? 0 : (+CONFIG.deliveryPrice || 0);
  }
  function deliveryNote() {
    const price = +CONFIG.deliveryPrice || 0, lim = +CONFIG.freeDeliveryFrom || 0;
    if (!price) return 'По городу, бесплатно';
    return lim ? `По городу, ${money(price)}. Бесплатно от ${money(lim)}` : `По городу, ${money(price)}`;
  }

  function cartItemHTML(it) {
    const p = byId[it.id], k = keyOf(it.id, it.sel), u = unitPrice(p, it.sel), o = optsText(p, it.sel);
    if (TH.cartItem) return TH.cartItem({ p, it, k, u, o });
    return `<li class="ci" data-key="${esc(k)}">
      <div class="ci-art">${art(p, it.sel.color)}</div>
      <div class="ci-body">
        <p class="ci-name">${esc(p.name)}</p>
        ${o ? `<p class="ci-opts">${esc(o)}</p>` : ''}
        <div class="ci-row">
          <div class="qty qty-sm" role="group" aria-label="Количество: ${esc(p.name)}">
            <button type="button" data-qty="-1" aria-label="Уменьшить количество">${ICON.minus}</button>
            <output>${it.qty}</output>
            <button type="button" data-qty="1" aria-label="Увеличить количество">${ICON.plus}</button>
          </div>
          <p class="ci-price">${money(u * it.qty)}</p>
        </div>
      </div>
      <button type="button" class="ci-remove" data-remove aria-label="Удалить из корзины: ${esc(p.name)}">${ICON.x}</button>
    </li>`;
  }

  function renderCart() {
    const n = cartCount();
    $$('.js-cart-count').forEach(el => { el.textContent = n; el.classList.toggle('is-zero', n === 0); });
    const list = $('#cartList');
    if (list) list.innerHTML = state.cart.map(cartItemHTML).join('');
    const empty = $('#cartEmpty');
    if (empty) empty.hidden = n > 0;
    const foot = $('#cartFoot');
    if (foot) foot.hidden = n === 0;
    const sub = cartSubtotal();
    $$('.js-cart-subtotal').forEach(el => { el.textContent = money(sub); });
    const fs = $('#freeShip');
    if (fs) {
      const lim = +CONFIG.freeDeliveryFrom || 0;
      fs.hidden = !lim;
      if (lim) {
        const left = Math.max(0, lim - sub);
        $('.js-fs-text', fs).textContent = left > 0 ? `До бесплатной доставки осталось ${money(left)}` : 'Доставка по городу будет бесплатной';
        $('.js-fs-bar', fs).style.width = Math.min(100, (sub / lim) * 100) + '%';
      }
    }
    if (isOpen('#checkoutModal')) renderCheckoutSummary();
  }

  function bindCart() {
    const list = $('#cartList');
    list.addEventListener('click', e => {
      const li = e.target.closest('[data-key]');
      if (!li) return;
      const k = li.dataset.key;
      const q = e.target.closest('[data-qty]');
      if (q) {
        const it = state.cart.find(x => keyOf(x.id, x.sel) === k);
        if (!it) return;
        const dir = q.dataset.qty;
        setQty(k, it.qty + (+dir));
        const again = $(`#cartList [data-key="${cssEsc(k)}"] [data-qty="${dir}"]`);
        if (again) again.focus();
        else { const first = $('#cartList [data-qty]') || $('#cartDrawer [data-close].icon-btn'); if (first) first.focus(); }
        return;
      }
      if (e.target.closest('[data-remove]')) {
        setQty(k, 0);
        const next = $('#cartList [data-remove]') || $('#cartDrawer .icon-btn[data-close]');
        if (next) next.focus();
      }
    });
  }

  let bumpT;
  function bump() {
    $$('.js-cart-count').forEach(el => { el.classList.remove('bump'); void el.offsetWidth; el.classList.add('bump'); });
    clearTimeout(bumpT);
    bumpT = setTimeout(() => $$('.js-cart-count').forEach(el => el.classList.remove('bump')), 600);
  }

  let toastT;
  function toast(msg, withCart) {
    const t = $('#toast');
    if (!t) return;
    $('#toastText').textContent = msg;
    const b = t.querySelector('[data-open-cart]');
    if (b) b.hidden = withCart === false;
    t.classList.add('is-on');
    clearTimeout(toastT);
    toastT = setTimeout(hideToast, 4000);
  }
  function hideToast() { const t = $('#toast'); if (t) t.classList.remove('is-on'); }

  /* ---------- слои: корзина и окна ---------- */
  const layers = [];
  const isOpen = sel => { const el = $(sel); return !!(el && el.classList.contains('is-open')); };
  function focusables(root) {
    return $$('a[href],button:not([disabled]),input:not([disabled]):not([type="hidden"]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])', root)
      .filter(x => x.getClientRects().length && !x.closest('[hidden]'));
  }
  function openLayer(el) {
    if (!el || el.classList.contains('is-open')) return;
    if (!layers.length) document.documentElement.style.setProperty('--sbw', (window.innerWidth - document.documentElement.clientWidth) + 'px');
    layers.push({ el, ret: document.activeElement });
    el.removeAttribute('inert');
    el.setAttribute('aria-hidden', 'false');
    el.classList.add('is-open');
    document.documentElement.classList.add('is-locked');
    setTimeout(() => {
      const f = el.querySelector('[data-autofocus]') || focusables(el)[0];
      if (f) f.focus({ preventScroll: true });
    }, 60);
  }
  function closeLayer(el, keepFocus) {
    const i = layers.findIndex(x => x.el === el);
    if (i < 0) return;
    const ret = layers.splice(i, 1)[0].ret;
    el.classList.remove('is-open');
    el.setAttribute('aria-hidden', 'true');
    el.setAttribute('inert', '');
    if (!layers.length) document.documentElement.classList.remove('is-locked');
    if (!keepFocus && ret && ret.focus && document.contains(ret)) ret.focus({ preventScroll: true });
  }

  function layersHTML() {
    const I = ICON;
    const rxRow = (side, label) => `<div class="rx-row"><span>${label}</span>` +
      `<input name="${side}_sph" inputmode="decimal" autocomplete="off" placeholder="-1.25" aria-label="${label}, SPH">` +
      `<input name="${side}_cyl" inputmode="decimal" autocomplete="off" placeholder="-0.50" aria-label="${label}, CYL">` +
      `<input name="${side}_ax" inputmode="numeric" autocomplete="off" placeholder="90" aria-label="${label}, AX"></div>`;
    return `
<aside class="layer drawer" id="cartDrawer" role="dialog" aria-modal="true" aria-labelledby="cartTitle" aria-hidden="true" inert>
  <div class="drawer-backdrop" data-close></div>
  <div class="drawer-box">
    <header class="drawer-head"><h2 id="cartTitle">Корзина</h2><button type="button" class="icon-btn" data-close aria-label="Закрыть корзину">${I.x}</button></header>
    <div class="drawer-body">
      <ul class="cart-list" id="cartList"></ul>
      <div class="cart-empty" id="cartEmpty">
        <span class="cart-empty-icon">${I.bag}</span>
        <p>В корзине пока пусто. В каталоге есть оправы, солнцезащитные очки и линзы.</p>
        <a class="btn btn-line" href="#catalog" data-close>Перейти в каталог</a>
      </div>
    </div>
    <footer class="drawer-foot" id="cartFoot" hidden>
      <div class="free-ship" id="freeShip"><p class="js-fs-text"></p><div class="bar"><i class="js-fs-bar"></i></div></div>
      <div class="cart-sum"><span>Сумма</span><b class="js-cart-subtotal"></b></div>
      <button type="button" class="btn btn-primary btn-block" data-checkout>Оформить заказ</button>
    </footer>
  </div>
</aside>

<div class="layer modal modal-product" id="productModal" role="dialog" aria-modal="true" aria-labelledby="pmName" aria-hidden="true" inert>
  <div class="modal-backdrop" data-close></div>
  <div class="modal-box pm">
    <button type="button" class="icon-btn modal-x" data-close aria-label="Закрыть">${I.x}</button>
    <div class="pm-art" id="pmArt"></div>
    <div class="pm-body">
      <p class="pm-cat" id="pmCat"></p>
      <h2 class="pm-name" id="pmName"></h2>
      <p class="pm-sub" id="pmSub"></p>
      <dl class="pm-info" id="pmInfo"></dl>
      <div class="pm-opts" id="pmOpts"></div>
      <div class="pm-foot">
        <div class="pm-buy">
          <div class="qty" role="group" aria-label="Количество">
            <button type="button" data-pm-qty="-1" aria-label="Уменьшить количество">${I.minus}</button>
            <output id="pmQtyVal">1</output>
            <button type="button" data-pm-qty="1" aria-label="Увеличить количество">${I.plus}</button>
          </div>
          <p class="pm-price"><span id="pmPrice"></span> <s id="pmOld" hidden></s></p>
        </div>
        <p class="form-error" id="pmError" role="alert" hidden></p>
        <button type="button" class="btn btn-primary btn-block" id="pmAdd">Добавить в корзину</button>
      </div>
    </div>
  </div>
</div>

<div class="layer modal modal-checkout" id="checkoutModal" role="dialog" aria-modal="true" aria-labelledby="coTitle" aria-hidden="true" inert>
  <div class="modal-backdrop" data-close></div>
  <form class="modal-box co" id="checkoutForm" novalidate>
    <header class="co-head"><h2 id="coTitle">Оформление заказа</h2><button type="button" class="icon-btn" data-close aria-label="Закрыть оформление">${I.x}</button></header>
    <div class="co-grid">
      <div class="co-fields">
        <fieldset class="co-set">
          <legend>Контакты</legend>
          <div class="row2">
            <div class="field"><label for="coName">Имя</label><input id="coName" name="name" type="text" autocomplete="name" required><p class="field-error"></p></div>
            <div class="field"><label for="coPhone">Телефон</label><input id="coPhone" name="phone" type="tel" autocomplete="tel" inputmode="tel" placeholder="+994 50 000 00 00" required><p class="field-error"></p></div>
          </div>
        </fieldset>
        <fieldset class="co-set">
          <legend>Получение</legend>
          <div class="choices">
            <label class="choice"><input type="radio" name="delivery" value="pickup" data-label="Самовывоз из салона" checked><span><b>Самовывоз из салона</b><small data-cfg="address"></small></span></label>
            <label class="choice"><input type="radio" name="delivery" value="courier" data-label="Доставка курьером"><span><b>Доставка курьером</b><small class="js-delivery-note"></small></span></label>
          </div>
          <div class="field" id="coAddressField" hidden><label for="coAddress">Адрес доставки</label><textarea id="coAddress" name="address" rows="2" autocomplete="street-address" placeholder="Улица, дом, квартира, ориентир"></textarea><p class="field-error"></p></div>
        </fieldset>
        <fieldset class="co-set">
          <legend>Оплата</legend>
          <div class="choices choices-3">
            <label class="choice"><input type="radio" name="payment" value="cash" data-label="Наличными при получении" checked><span><b>Наличными</b><small>При получении</small></span></label>
            <label class="choice"><input type="radio" name="payment" value="card" data-label="Картой при получении"><span><b>Картой</b><small>При получении</small></span></label>
            <label class="choice"><input type="radio" name="payment" value="transfer" data-label="Переводом на карту"><span><b>Переводом</b><small>Реквизиты пришлём в WhatsApp</small></span></label>
          </div>
        </fieldset>
        <fieldset class="co-set" id="rxBlock" hidden>
          <legend>Рецепт для линз</legend>
          <div class="choices choices-rx">
            <label class="choice"><input type="radio" name="rxMode" value="enter" data-label="Данные рецепта"><span><b>Введу данные рецепта</b></span></label>
            <label class="choice"><input type="radio" name="rxMode" value="photo" data-label="Пришлю фото рецепта в этот чат"><span><b>Пришлю фото рецепта в WhatsApp</b></span></label>
            <label class="choice"><input type="radio" name="rxMode" value="exam" data-label="Нужна проверка зрения в салоне"><span><b>Нужна проверка зрения в салоне</b></span></label>
            <label class="choice" data-rx-none><input type="radio" name="rxMode" value="none" data-label="Линзы не нужны, только оправа"><span><b>Линзы не нужны, только оправа</b></span></label>
          </div>
          <div class="field rx-field" id="rxGrid" hidden>
            <div class="rx" role="group" aria-label="Данные рецепта">
              <div class="rx-row rx-head" aria-hidden="true"><span></span><span>SPH</span><span>CYL</span><span>AX</span></div>
              ${rxRow('od', 'Правый (OD)')}
              ${rxRow('os', 'Левый (OS)')}
              <label class="rx-pd"><span>Межзрачковое расстояние, PD</span><input name="pd" inputmode="decimal" autocomplete="off" placeholder="62"></label>
            </div>
            <p class="hint">Значения есть в рецепте от врача. CYL и AX заполняйте, только если они указаны.</p>
            <p class="field-error"></p>
          </div>
        </fieldset>
        <div class="field"><label for="coComment">Комментарий <span class="opt-note">(необязательно)</span></label><textarea id="coComment" name="comment" rows="2" placeholder="Удобное время доставки, вопросы по заказу"></textarea></div>
      </div>
      <aside class="co-summary" aria-label="Ваш заказ">
        <h3>Ваш заказ</h3>
        <ul class="co-items" id="coItems"></ul>
        <dl class="co-totals">
          <div><dt>Товары</dt><dd id="coSubtotal"></dd></div>
          <div><dt>Доставка</dt><dd id="coDelivery"></dd></div>
          <div class="co-total"><dt>Итого</dt><dd id="coTotal"></dd></div>
        </dl>
        <button type="submit" class="btn btn-primary btn-block btn-wa">${I.chat}<span>Отправить заказ в WhatsApp</span></button>
        <p class="co-note">Откроется WhatsApp с готовым текстом заказа. Нажмите в нём «Отправить», и заказ придёт к нам.</p>
      </aside>
    </div>
  </form>
</div>

<div class="layer modal modal-ok" id="successModal" role="dialog" aria-modal="true" aria-labelledby="okTitle" aria-hidden="true" inert>
  <div class="modal-backdrop" data-close></div>
  <div class="modal-box ok">
    <span class="ok-icon">${I.check}</span>
    <h2 id="okTitle"></h2>
    <p id="okText"></p>
    <a class="btn btn-primary btn-block" id="okWa" href="#" target="_blank" rel="noopener">${I.chat}<span>Открыть WhatsApp ещё раз</span></a>
    <button type="button" class="btn btn-line btn-block" data-close>Вернуться на сайт</button>
  </div>
</div>

<div class="toast" id="toast" role="status" aria-live="polite"><span id="toastText"></span><button type="button" data-open-cart>Открыть корзину</button></div>
<a class="wa-float" data-cfg-href="wa" href="#" target="_blank" rel="noopener" aria-label="Написать нам в WhatsApp">${I.chat}</a>`;
  }

  function repairFormHTML(title) {
    return `<h3 class="rf-title">${esc(title || 'Заявка на ремонт')}</h3>
      <div class="row2">
        <div class="field"><label for="rpName">Имя</label><input id="rpName" name="name" type="text" autocomplete="name" required><p class="field-error"></p></div>
        <div class="field"><label for="rpPhone">Телефон</label><input id="rpPhone" name="phone" type="tel" autocomplete="tel" inputmode="tel" placeholder="+994 50 000 00 00" required><p class="field-error"></p></div>
      </div>
      <fieldset class="field"><legend>Что нужно сделать</legend><div class="chips" id="rpServices"></div><p class="field-error"></p></fieldset>
      <div class="field"><label for="rpDesc">Опишите поломку <span class="opt-note">(необязательно)</span></label><textarea id="rpDesc" name="desc" rows="3" placeholder="Например: отломился заушник у металлической оправы"></textarea></div>
      <fieldset class="field"><legend>Как передадите очки</legend>
        <div class="choices choices-2">
          <label class="choice"><input type="radio" name="handover" value="salon" data-label="Принесу очки в салон" checked><span><b>Принесу в салон</b></span></label>
          <label class="choice"><input type="radio" name="handover" value="courier" data-label="Нужен курьер, чтобы забрать очки"><span><b>Заберите курьером</b></span></label>
        </div>
      </fieldset>
      <div class="field" id="rpAddressField" hidden><label for="rpAddress">Откуда забрать очки</label><textarea id="rpAddress" name="address" rows="2" autocomplete="street-address" placeholder="Улица, дом, квартира"></textarea><p class="field-error"></p></div>
      <div class="field"><label for="rpDate">Удобная дата <span class="opt-note">(необязательно)</span></label><input id="rpDate" name="date" type="date"></div>
      <button type="submit" class="btn btn-primary btn-block btn-wa">${ICON.chat}<span>Отправить заявку в WhatsApp</span></button>
      <p class="form-note">Фото поломки можно прикрепить в WhatsApp, когда откроется чат.</p>`;
  }

  /* ---------- формы: ошибки и помощники ---------- */
  let errSeq = 0;
  function setError(el, msg) {
    const fld = el.closest('.field') || el.parentElement;
    fld.classList.add('is-invalid');
    let p = $('.field-error', fld);
    if (!p) { p = document.createElement('p'); p.className = 'field-error'; fld.appendChild(p); }
    if (!p.id) p.id = 'err-' + (++errSeq);
    p.textContent = msg;
    el.setAttribute('aria-invalid', 'true');
    el.setAttribute('aria-describedby', p.id);
  }
  function clearFieldError(fld) {
    fld.classList.remove('is-invalid');
    const p = $('.field-error', fld);
    if (p) p.textContent = '';
    $$('[aria-invalid]', fld).forEach(x => x.removeAttribute('aria-invalid'));
  }
  const clearErrors = f => $$('.field.is-invalid', f).forEach(clearFieldError);
  const val = (f, n) => (f.elements[n] && f.elements[n].value != null ? String(f.elements[n].value).trim() : '');
  const radioVal = (f, n) => { const r = f.querySelector(`input[name="${n}"]:checked`); return r ? r.value : ''; };
  const radioLabel = (f, n) => { const r = f.querySelector(`input[name="${n}"]:checked`); return r ? (r.dataset.label || r.value) : ''; };
  function setRadio(f, n, v) { const r = f.querySelector(`input[name="${n}"][value="${v}"]`); if (r) r.checked = true; }
  function toggleField(f, name, value, sel) { const el = $(sel); if (el) el.hidden = radioVal(f, name) !== value; }

  function bindPhone(inp) {
    const pre = CONFIG.phonePrefix || '';
    inp.addEventListener('focus', () => {
      if (!inp.value && pre) {
        inp.value = pre;
        setTimeout(() => { try { inp.setSelectionRange(inp.value.length, inp.value.length); } catch (e) { /* ничего */ } }, 0);
      }
    });
    const cc = pre.replace(/\D/g, '');
    inp.addEventListener('blur', () => {
      if (pre && inp.value.trim() === pre.trim()) { inp.value = ''; return; }
      // «+994 994 50…» → «+994 50…», если код страны набрали дважды
      if (cc && inp.value.replace(/\D/g, '').indexOf(cc + cc) === 0) inp.value = inp.value.replace(cc, '').replace(/^\+\s*/, '+').replace(/^\+(\d)/, '+$1');
      // «+994 050…» → «+994 50…»: в международном формате ноль после кода страны не набирают
      const head = pre.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      if (head) inp.value = inp.value.replace(new RegExp('^(' + head + '\\s*)0(?=\\d)'), '$1');
    });
    inp.addEventListener('input', () => {
      let v = inp.value.replace(/[^\d+()\-\s]/g, '');
      const i = v.lastIndexOf('+');
      if (i > 0) v = v.slice(i);          // вставили номер целиком поверх «+994 »
      if (v !== inp.value) inp.value = v;
    });
  }
  function prefill(f) {
    const c = store.get(CUSTOMER_KEY, null);
    if (!c || !f) return;
    ['name', 'phone', 'address'].forEach(k => { if (f.elements[k] && !f.elements[k].value && c[k]) f.elements[k].value = c[k]; });
  }
  function saveCustomer(f) {
    const c = store.get(CUSTOMER_KEY, {}) || {};
    ['name', 'phone', 'address'].forEach(k => { const v = val(f, k); if (v) c[k] = v; });
    store.set(CUSTOMER_KEY, c);
  }
  function waUrl(text) {
    const num = String(CONFIG.whatsapp || '').replace(/\D/g, '');
    return 'https://wa.me/' + num + (text ? '?text=' + encodeURIComponent(text) : '');
  }
  function openWA(url) {
    const w = window.open(url, '_blank');
    if (w) { try { w.opener = null; } catch (e) { /* ничего */ } } else { window.location.href = url; }
  }
  function showSuccess(kind, id, url) {
    $('#okTitle').textContent = kind === 'order' ? 'Осталось отправить заказ' : 'Осталось отправить заявку';
    $('#okText').innerHTML = kind === 'order'
      ? `Мы открыли WhatsApp с текстом заказа <b>${esc(id)}</b>. Нажмите в чате «Отправить», и менеджер подтвердит заказ и время доставки.`
      : `Мы открыли WhatsApp с текстом заявки <b>${esc(id)}</b>. Нажмите в чате «Отправить», и мастер ответит со сроком и стоимостью ремонта.`;
    $('#okWa').href = url;
    openLayer($('#successModal'));
  }

  /* ---------- оформление заказа ---------- */
  function openCheckout() {
    if (!state.cart.length) return;
    const dr = $('#cartDrawer');
    if (dr && dr.classList.contains('is-open')) closeLayer(dr, true);
    const f = $('#checkoutForm');
    prefill(f);
    toggleField(f, 'delivery', 'courier', '#coAddressField');
    setupRx();
    renderCheckoutSummary();
    openLayer($('#checkoutModal'));
  }
  function renderCheckoutSummary() {
    const f = $('#checkoutForm');
    if (!f) return;
    const sub = cartSubtotal(), method = radioVal(f, 'delivery') || 'pickup', del = deliveryCost(sub, method);
    $('#coItems').innerHTML = state.cart.map(it => {
      const p = byId[it.id], u = unitPrice(p, it.sel), o = optsText(p, it.sel);
      return `<li><span class="co-i-name">${esc(p.name)}${o ? `<small>${esc(o)}</small>` : ''}</span><span class="co-i-qty">${it.qty}${NB}шт.</span><span class="co-i-sum">${money(u * it.qty)}</span></li>`;
    }).join('');
    $('#coSubtotal').textContent = money(sub);
    $('#coDelivery').textContent = method === 'courier' ? (del ? money(del) : 'бесплатно') : 'самовывоз';
    $('#coTotal').textContent = money(sub + del);
  }
  function setupRx() {
    const box = $('#rxBlock'), f = $('#checkoutForm');
    if (!box) return;
    const need = state.cart.some(it => byId[it.id].rx);
    box.hidden = !need;
    if (!need) return;
    const hasLenses = state.cart.some(it => byId[it.id].cat === 'lenses');
    const none = $('[data-rx-none]', box);
    if (none) none.hidden = hasLenses;
    const cur = radioVal(f, 'rxMode');
    if (!cur || (cur === 'none' && hasLenses)) setRadio(f, 'rxMode', hasLenses ? 'enter' : 'none');
    toggleField(f, 'rxMode', 'enter', '#rxGrid');
  }

  function submitOrder(e) {
    e.preventDefault();
    const f = e.currentTarget;
    if (!state.cart.length) { closeLayer($('#checkoutModal')); return; }
    clearErrors(f);
    const errs = [];
    if (val(f, 'name').length < 2) errs.push([f.elements.name, 'Укажите имя']);
    if (digitsCount(val(f, 'phone')) < 9) errs.push([f.elements.phone, 'Укажите номер телефона полностью']);
    const method = radioVal(f, 'delivery');
    if (method === 'courier' && val(f, 'address').length < 5) errs.push([f.elements.address, 'Укажите адрес доставки']);
    const rxOn = !$('#rxBlock').hidden;
    const rxMode = radioVal(f, 'rxMode');
    if (rxOn && rxMode === 'enter' && !val(f, 'od_sph') && !val(f, 'os_sph')) {
      errs.push([f.elements.od_sph, 'Заполните SPH хотя бы для одного глаза или выберите «Пришлю фото рецепта в WhatsApp»']);
    }
    if (errs.length) { errs.forEach(x => setError(x[0], x[1])); errs[0][0].focus(); return; }

    const sub = cartSubtotal(), del = deliveryCost(sub, method), id = makeId('OP');
    const L = ['Здравствуйте! Хочу оформить заказ.', '', `*Заказ ${id}*`, nowStr(), '', '*Товары:*'];
    state.cart.forEach((it, i) => {
      const p = byId[it.id], u = unitPrice(p, it.sel), o = optsLong(p, it.sel);
      L.push(`${i + 1}. ${p.name}`);
      if (o) L.push(`    ${o}`);
      L.push(`    ${it.qty} × ${money(u)} = ${money(u * it.qty)}`);
    });
    L.push('', `Товары: ${money(sub)}`);
    L.push(`Доставка: ${method === 'courier' ? (del ? money(del) : 'бесплатно') : 'самовывоз'}`);
    L.push(`*Итого к оплате: ${money(sub + del)}*`, '', '*Покупатель:*');
    L.push(`Имя: ${val(f, 'name')}`, `Телефон: ${val(f, 'phone')}`, `Получение: ${radioLabel(f, 'delivery')}`);
    if (method === 'courier') L.push(`Адрес: ${val(f, 'address')}`);
    L.push(`Оплата: ${radioLabel(f, 'payment')}`);
    if (rxOn) {
      L.push('', '*Рецепт:*');
      if (rxMode === 'enter') {
        const eye = s => [['SPH', val(f, s + '_sph')], ['CYL', val(f, s + '_cyl')], ['AX', val(f, s + '_ax')]]
          .filter(x => x[1]).map(x => x[0] + ' ' + x[1]).join(', ') || 'не указано';
        L.push(`OD (правый): ${eye('od')}`, `OS (левый): ${eye('os')}`);
        if (val(f, 'pd')) L.push(`PD: ${val(f, 'pd')} мм`);
      } else {
        L.push(radioLabel(f, 'rxMode'));
      }
    }
    if (val(f, 'comment')) L.push('', `Комментарий: ${val(f, 'comment')}`);

    const url = waUrl(L.join('\n'));
    saveCustomer(f);
    prefill($('#repairForm'));
    openWA(url);
    state.cart = [];
    saveCart();
    renderCart();
    ['comment', 'od_sph', 'od_cyl', 'od_ax', 'os_sph', 'os_cyl', 'os_ax', 'pd'].forEach(n => { if (f.elements[n]) f.elements[n].value = ''; });
    $$('input[name="rxMode"]', f).forEach(r => { r.checked = false; });
    closeLayer($('#checkoutModal'), true);
    showSuccess('order', id, url);
  }

  /* ---------- заявка на ремонт ---------- */
  function renderServices() {
    const list = $('#servicesList');
    if (list) {
      list.innerHTML = SERVICES.map(s => (TH.service ? TH.service(s, svcPrice(s)) :
        `<li><button type="button" class="svc" data-svc="${s.id}" aria-pressed="false"><span class="svc-name">${esc(s.name)}</span><span class="svc-time">${esc(s.time)}</span><span class="svc-price">${svcPrice(s)}</span></button></li>`)).join('');
    }
    const form = $('#repairForm');
    if (form && !form.children.length) form.innerHTML = repairFormHTML(form.dataset.title);
    const chips = $('#rpServices');
    if (chips) {
      chips.innerHTML = SERVICES.map(s =>
        `<label class="chip"><input type="checkbox" name="svc" value="${esc(s.name)}" data-svc-id="${s.id}"><span>${esc(s.name)}</span></label>`).join('');
    }
    const date = $('#rpDate');
    if (date) { const d = new Date(); date.min = `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())}`; }
  }
  const svcPrice = s => (s.from ? 'от ' : '') + money(s.price);
  function syncServiceRows() {
    $$('[data-svc]').forEach(b => {
      const cb = $(`#rpServices input[data-svc-id="${cssEsc(b.dataset.svc)}"]`);
      const on = !!(cb && cb.checked);
      b.classList.toggle('is-picked', on);
      b.setAttribute('aria-pressed', on);
    });
  }
  function pickService(id) {
    const cb = $(`#rpServices input[data-svc-id="${cssEsc(id)}"]`);
    if (!cb) return;
    cb.checked = !cb.checked;
    const fld = cb.closest('.field');
    if (fld) clearFieldError(fld);
    syncServiceRows();
    if (cb.checked) {
      const chip = cb.closest('.chip');
      chip.classList.remove('flash'); void chip.offsetWidth; chip.classList.add('flash');
      const s = SERVICES.find(x => x.id === id);
      toast('Добавлено в заявку: ' + (s ? s.name : ''), false);
      const form = $('#repairForm');
      const r = form.getBoundingClientRect();
      if (r.top > window.innerHeight * 0.8 || r.bottom < 80) form.scrollIntoView({ behavior: reduced() ? 'auto' : 'smooth', block: 'start' });
    }
  }
  // Кнопка «Записаться на проверку зрения» и подобные: отмечает услугу и ведёт к форме
  function selectService(id) {
    const cb = $(`#rpServices input[data-svc-id="${cssEsc(id)}"]`);
    if (!cb) return;
    cb.checked = true;
    const fld = cb.closest('.field');
    if (fld) clearFieldError(fld);
    syncServiceRows();
    const chip = cb.closest('.chip');
    chip.classList.remove('flash'); void chip.offsetWidth; chip.classList.add('flash');
    const form = $('#repairForm');
    form.scrollIntoView({ behavior: reduced() ? 'auto' : 'smooth', block: 'start' });
    setTimeout(() => {
      const n = form.elements.name;
      if (n && !n.value) n.focus({ preventScroll: true });
    }, reduced() ? 0 : 700);
  }
  function submitRepair(e) {
    e.preventDefault();
    const f = e.currentTarget;
    clearErrors(f);
    const svcs = $$('input[name="svc"]:checked', f).map(i => i.value);
    const errs = [];
    if (val(f, 'name').length < 2) errs.push([f.elements.name, 'Укажите имя']);
    if (digitsCount(val(f, 'phone')) < 9) errs.push([f.elements.phone, 'Укажите номер телефона полностью']);
    if (!svcs.length) errs.push([$('input[name="svc"]', f), 'Выберите хотя бы одну услугу']);
    const how = radioVal(f, 'handover');
    if (how === 'courier' && val(f, 'address').length < 5) errs.push([f.elements.address, 'Укажите адрес, откуда забрать очки']);
    if (errs.length) { errs.forEach(x => setError(x[0], x[1])); errs[0][0].focus(); return; }

    const id = makeId('R');
    const L = ['Здравствуйте! Хочу оставить заявку на ремонт очков.', '', `*Заявка ${id}*`, nowStr(), '', `Что сделать: ${svcs.join(', ')}`];
    if (val(f, 'desc')) L.push(`Описание: ${val(f, 'desc')}`);
    L.push(`Передача очков: ${radioLabel(f, 'handover')}`);
    if (how === 'courier') L.push(`Адрес: ${val(f, 'address')}`);
    const d = val(f, 'date');
    if (d) { const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(d); L.push(`Удобная дата: ${m ? `${m[3]}.${m[2]}.${m[1]}` : d}`); }
    L.push('', '*Клиент:*', `Имя: ${val(f, 'name')}`, `Телефон: ${val(f, 'phone')}`);

    const url = waUrl(L.join('\n'));
    saveCustomer(f);
    prefill($('#checkoutForm'));
    openWA(url);
    $$('input[name="svc"]', f).forEach(i => { i.checked = false; });
    if (f.elements.desc) f.elements.desc.value = '';
    if (f.elements.date) f.elements.date.value = '';
    syncServiceRows();
    showSuccess('repair', id, url);
  }

  /* ---------- контакты из настроек ---------- */
  function fillConfig() {
    const map = {
      shopName: CONFIG.shopName, phone: CONFIG.phone, address: CONFIG.address,
      year: String(new Date().getFullYear()), instagram: CONFIG.instagram ? '@' + CONFIG.instagram : '',
      delivery: deliveryNote(), freeFrom: CONFIG.freeDeliveryFrom ? money(CONFIG.freeDeliveryFrom) : '',
      deliveryPrice: money(CONFIG.deliveryPrice || 0),
    };
    $$('[data-cfg]').forEach(el => {
      const k = el.dataset.cfg;
      if (k === 'hours') el.innerHTML = (CONFIG.hours || []).map(esc).join('<br>');
      else if (map[k] != null) el.textContent = map[k];
    });
    $$('.js-delivery-note').forEach(el => { el.textContent = deliveryNote(); });
    const wa = waUrl('Здравствуйте! У меня вопрос.');
    $$('[data-cfg-href]').forEach(el => {
      const k = el.dataset.cfgHref;
      if (k === 'wa') el.href = wa;
      else if (k === 'tel') el.href = 'tel:' + String(CONFIG.phone).replace(/[^\d+]/g, '');
      else if (k === 'map') el.href = 'https://maps.google.com/?q=' + encodeURIComponent(CONFIG.mapQuery || CONFIG.address);
      else if (k === 'ig') {
        if (CONFIG.instagram) el.href = 'https://instagram.com/' + encodeURIComponent(CONFIG.instagram);
        else (el.closest('[data-cfg-wrap]') || el).hidden = true;
      }
    });
    $$('iframe[data-cfg-map]').forEach(fr => {
      fr.src = 'https://maps.google.com/maps?q=' + encodeURIComponent(CONFIG.mapQuery || CONFIG.address) + '&z=15&output=embed';
    });
    if (CONFIG.shopName && CONFIG.shopName !== 'Optika') document.title = document.title.replace(/Optika/g, CONFIG.shopName);
    if (/^9940+$/.test(String(CONFIG.whatsapp))) console.warn('Optika: укажите свой номер WhatsApp в CONFIG.whatsapp, чтобы заказы приходили вам.');
  }

  /* ---------- шапка и меню ---------- */
  function closeMenu() {
    document.body.classList.remove('menu-open');
    $$('.js-menu-toggle').forEach(b => b.setAttribute('aria-expanded', 'false'));
  }
  function bindNav() {
    $$('.js-menu-toggle').forEach(tg => tg.addEventListener('click', () => {
      const on = !document.body.classList.contains('menu-open');
      document.body.classList.toggle('menu-open', on);
      tg.setAttribute('aria-expanded', on);
    }));
    const nav = $('#siteNav');
    if (nav) nav.addEventListener('click', e => { if (e.target.closest('a')) closeMenu(); });
    const header = $('.site-header');
    if (header) {
      const on = () => header.classList.toggle('is-scrolled', window.scrollY > 8);
      window.addEventListener('scroll', on, { passive: true });
      on();
    }
  }

  function onDocClick(e) {
    const t = e.target;
    const close = t.closest('[data-close]');
    if (close) {
      const layer = close.closest('.layer');
      if (layer) {
        const href = close.getAttribute('href');
        if (!(href && href.charAt(0) === '#')) e.preventDefault();
        closeLayer(layer);
      }
      return;
    }
    if (t.closest('[data-open-cart]')) { e.preventDefault(); hideToast(); openLayer($('#cartDrawer')); return; }
    if (t.closest('[data-checkout]')) { e.preventDefault(); openCheckout(); return; }
    const ps = t.closest('[data-pick-svc]');
    if (ps) { e.preventDefault(); selectService(ps.dataset.pickSvc); return; }
    const g = t.closest('[data-goto]');
    if (g) {
      state.cat = g.dataset.goto;
      state.q = '';
      const si = $('#searchInput');
      if (si) si.value = '';
      renderProducts();
      closeMenu();
    }
  }

  function onKey(e) {
    if (!layers.length) {
      if (e.key === 'Escape' && document.body.classList.contains('menu-open')) closeMenu();
      return;
    }
    const top = layers[layers.length - 1].el;
    if (e.key === 'Escape') { e.preventDefault(); closeLayer(top); return; }
    if (e.key === 'Tab') {
      const f = focusables(top);
      if (!f.length) return;
      const first = f[0], last = f[f.length - 1];
      if (!top.contains(document.activeElement)) { e.preventDefault(); first.focus(); }
      else if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  }

  function bindAll() {
    const tabs = $('#catTabs');
    if (tabs) tabs.addEventListener('click', e => { const b = e.target.closest('[data-cat]'); if (b) { state.cat = b.dataset.cat; renderProducts(); } });
    const si = $('#searchInput');
    if (si) {
      let t;
      si.addEventListener('input', () => { clearTimeout(t); t = setTimeout(() => { state.q = si.value.trim(); renderProducts(); }, 120); });
    }
    const so = $('#sortSelect');
    if (so) so.addEventListener('change', () => { state.sort = so.value; renderProducts(); });
    $$('[data-reset-filter]').forEach(b => b.addEventListener('click', () => {
      state.cat = 'all'; state.q = '';
      if (si) si.value = '';
      renderProducts();
    }));
    const grid = $('#productsGrid');
    if (grid) grid.addEventListener('click', onGridClick);

    bindProductModal();
    bindCart();

    const cf = $('#checkoutForm');
    cf.addEventListener('submit', submitOrder);
    cf.addEventListener('change', e => {
      const n = e.target.name;
      if (n === 'delivery') { toggleField(cf, 'delivery', 'courier', '#coAddressField'); renderCheckoutSummary(); }
      if (n === 'rxMode') toggleField(cf, 'rxMode', 'enter', '#rxGrid');
    });
    cf.addEventListener('input', e => { const fld = e.target.closest('.field'); if (fld && fld.classList.contains('is-invalid')) clearFieldError(fld); });

    const rf = $('#repairForm');
    if (rf) {
      rf.addEventListener('submit', submitRepair);
      rf.addEventListener('change', e => {
        if (e.target.name === 'handover') toggleField(rf, 'handover', 'courier', '#rpAddressField');
        if (e.target.name === 'svc') syncServiceRows();
        const fld = e.target.closest('.field');
        if (fld && fld.classList.contains('is-invalid')) clearFieldError(fld);
      });
      rf.addEventListener('input', e => { const fld = e.target.closest('.field'); if (fld && fld.classList.contains('is-invalid')) clearFieldError(fld); });
    }
    const sl = $('#servicesList');
    if (sl) sl.addEventListener('click', e => { const b = e.target.closest('[data-svc]'); if (b) pickService(b.dataset.svc); });

    $$('input[type="tel"]').forEach(bindPhone);
    document.addEventListener('click', onDocClick);
    document.addEventListener('keydown', onKey);
    bindNav();
  }

  /* ---------- запуск ---------- */
  window.Shop = {
    CONFIG, state, byId, art, glasses, money, esc, plural, swatches, swAttr, badges, needsOptions, priceLabel, catName,
    colorOf, hexA, icon: n => ICON[n] || '', openProduct, toast, reduced, waUrl,
    render: () => renderProducts(),
    setFilter(cat, q) {
      state.cat = cat || 'all';
      state.q = q || '';
      const si = $('#searchInput');
      if (si) si.value = q || '';
      renderProducts();
    },
  };

  function init() {
    injectDefs();
    const wrap = document.createElement('div');
    wrap.innerHTML = layersHTML();
    while (wrap.firstChild) document.body.appendChild(wrap.firstChild);
    renderServices();
    $$('[data-icon]').forEach(el => { el.innerHTML = ICON[el.dataset.icon] || ''; });
    fillConfig();
    loadCart();
    renderTabs();
    renderProducts();
    renderCart();
    bindAll();
    prefill($('#repairForm'));
    if (TH.onInit) TH.onInit();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
