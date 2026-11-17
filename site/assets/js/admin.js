/* Админ-панель: меню на телефоне, подтверждение удаления, цвет рядом с кодом цвета, язык полей, подготовка фото к загрузке */
(function () {
  'use strict';
  /* Надписи на языке админ-панели приходят вместе со страницей; без них остаются русские. */
  var T = {};
  try { T = JSON.parse(document.getElementById('ao-i18n').textContent) || {}; } catch (err) { /* русские надписи */ }
  function tx(key, ru, vars) {
    var s = typeof T[key] === 'string' && T[key] ? T[key] : ru, k;
    for (k in vars || {}) s = s.split('{' + k + '}').join(vars[k]);
    return s;
  }
  var side = document.querySelector('.side'), btn = document.querySelector('.menu-btn');
  if (side && btn) {
    btn.addEventListener('click', function () {
      var on = !side.classList.contains('is-open');
      side.classList.toggle('is-open', on);
      btn.setAttribute('aria-expanded', on);
    });
  }
  document.addEventListener('submit', function (e) {
    var form = e.target, msg = form.getAttribute && form.getAttribute('data-confirm');
    if (msg && !window.confirm(msg)) return e.preventDefault();
    // Если фото ещё готовится к загрузке, форма уйдёт сразу после этого, а не с исходным большим файлом
    var waiting = [].filter.call(form.querySelectorAll ? form.querySelectorAll('input[type=file]') : [], function (i) { return i._prep; }).map(function (i) { return i._prep; });
    if (!waiting.length) return;
    e.preventDefault();
    var by = e.submitter;
    Promise.all(waiting).then(function () {
      if (form.requestSubmit) form.requestSubmit(by && by.form === form ? by : undefined); else form.submit();
    });
  });
  document.addEventListener('input', function (e) {
    var el = e.target;
    if (!el.closest || !el.closest('.color-row') || el.name.slice(-3) !== '[c]') return;
    var sw = el.closest('.color-row').querySelector('.sw');
    if (sw) sw.style.background = /^#[0-9a-f]{3,8}$/i.test(el.value.trim()) ? el.value.trim() : 'transparent';
  });

  /* Язык текстов в формах: видны поля одного языка, выбор держится до закрытия вкладки.
     Сначала открыт язык админ-панели. Если форма вернулась с ошибкой в поле другого языка, открывается он. */
  var LG = ['ru', 'az', 'en'];
  var UI = LG.indexOf(document.documentElement.lang) < 0 ? 'ru' : document.documentElement.lang, KEEP = 'ao-lg-' + UI;
  function setLang(l) {
    if (LG.indexOf(l) < 0) l = UI;
    document.documentElement.setAttribute('data-lg', l);
    [].forEach.call(document.querySelectorAll('[data-lg-set]'), function (b) {
      b.setAttribute('aria-pressed', b.getAttribute('data-lg-set') === l ? 'true' : 'false');
    });
    try { sessionStorage.setItem(KEEP, l); } catch (err) { /* без памяти вкладки просто не запоминаем */ }
  }
  if (document.querySelector('.lang[data-lg]') && document.querySelector('[data-lg-set]')) {
    var first = UI;
    try { first = sessionStorage.getItem(KEEP) || UI; } catch (err) { /* ничего */ }
    var bad = document.querySelector('.field.is-invalid .lang .err');
    bad = bad ? bad.closest('.lang') : null;
    if (!bad) {
      var wrong = document.querySelector('.field.is-invalid .langs');
      if (wrong) {
        bad = [].filter.call(wrong.querySelectorAll('.lang'), function (x) {
          var i = x.querySelector('input,textarea');
          return i && !i.value.trim();
        })[0] || null;
      }
    }
    setLang(bad ? bad.getAttribute('data-lg') : first);
    document.addEventListener('click', function (e) {
      var b = e.target.closest ? e.target.closest('[data-lg-set]') : null;
      if (b) setLang(b.getAttribute('data-lg-set'));
    });
  }

  /* Фото уменьшается прямо в браузере до 2000 точек по длинной стороне:
     большой снимок с телефона проходит любой хостинг и загружается за секунды. Сервер всё равно проверяет и пересохраняет файл. */
  var MAX_SIDE = 2000, KEEP_UNDER = 1500000;
  function size(n) {
    return n >= 1048576 ? (n / 1048576).toFixed(1).replace('.', ',') + ' ' + tx('mb', 'МБ') : Math.max(1, Math.round(n / 1024)) + ' ' + tx('kb', 'КБ');
  }
  function note(input, text, bad) {
    var p = input.parentNode.querySelector('.file-note');
    if (!p) return;
    p.hidden = !text;
    p.textContent = text;
    p.classList.toggle('is-bad', !!bad);
  }
  function preview(input, file) {
    var box = input.closest('.imgf'), img = box && box.querySelector('.thumb');
    if (!box || !window.URL || !URL.createObjectURL) return;
    if (!img) {
      img = document.createElement('img');
      img.className = 'thumb';
      img.alt = '';
      box.insertBefore(img, box.firstChild);
    }
    if (img.dataset.blob) URL.revokeObjectURL(img.dataset.blob);
    img.dataset.blob = img.src = URL.createObjectURL(file);
  }
  function shrink(file) {
    if (!window.createImageBitmap || !window.DataTransfer || !window.File || !HTMLCanvasElement.prototype.toBlob) return Promise.resolve(file);
    return createImageBitmap(file, { imageOrientation: 'from-image' }).then(function (bmp) {
      var k = Math.min(1, MAX_SIDE / Math.max(bmp.width, bmp.height));
      if (k === 1 && file.size <= KEEP_UNDER) return file;
      var c = document.createElement('canvas'), png = file.type === 'image/png';
      c.width = Math.max(1, Math.round(bmp.width * k));
      c.height = Math.max(1, Math.round(bmp.height * k));
      var ctx = c.getContext('2d');
      if (!png) {   // у PNG сохраняем прозрачный фон, остальным подкладываем белый
        ctx.fillStyle = '#fff';
        ctx.fillRect(0, 0, c.width, c.height);
      }
      ctx.imageSmoothingQuality = 'high';
      ctx.drawImage(bmp, 0, 0, c.width, c.height);
      if (bmp.close) bmp.close();
      return new Promise(function (resolve) {
        c.toBlob(function (blob) {
          if (!blob || blob.size >= file.size) return resolve(file);
          var ext = blob.type === 'image/webp' ? 'webp' : (blob.type === 'image/png' ? 'png' : 'jpg');
          resolve(new File([blob], file.name.replace(/\.[^.]*$/, '') + '.' + ext, { type: blob.type }));
        }, png ? 'image/webp' : 'image/jpeg', png ? 0.9 : 0.86);
      });
    }).catch(function () { return file; });
  }
  document.addEventListener('change', function (e) {
    var input = e.target;
    if (!input.matches || !input.matches('input[type=file][data-max]') || input.dataset.busy) return;
    var file = input.files && input.files[0];
    if (!file) return note(input, '');
    if (!/^image\/(jpeg|png|webp)$/.test(file.type)) {
      input.value = '';
      return note(input, tx('fileBad', 'Файл «{name}» не подходит: нужна картинка JPG, PNG или WebP.', { name: file.name }), true);
    }
    var max = parseInt(input.getAttribute('data-max'), 10) || 0;
    note(input, tx('filePrep', 'Готовлю фото…'));
    input._prep = shrink(file).then(function (out) {
      input._prep = null;
      if (out !== file) {
        try {
          var dt = new DataTransfer();
          dt.items.add(out);
          input.dataset.busy = '1';
          input.files = dt.files;
          delete input.dataset.busy;
        } catch (err) { out = file; }
      }
      preview(input, out);
      if (max && out.size > max) return note(input, tx('fileBig', 'Файл {size} — больше, чем принимает хостинг ({max}). Уменьшите фото и выберите его снова.', { size: size(out.size), max: size(max) }), true);
      note(input, out !== file ? tx('fileSmall', 'Фото уменьшено: {from} → {to}. Нажмите «Сохранить».', { from: size(file.size), to: size(out.size) })
        : tx('fileOk', 'Фото выбрано: {size}. Нажмите «Сохранить».', { size: size(out.size) }));
    });
  });

  /* Счётчик знаков у SEO-полей: что длиннее нормы, поисковик обрежет. Пустое поле считает текст, который сайт поставит сам. */
  [].forEach.call(document.querySelectorAll('[data-count]'), function (el) {
    var max = parseInt(el.getAttribute('data-count'), 10) || 0;
    var out = document.createElement('span');
    out.className = 'count';
    el.parentNode.appendChild(out);
    function update() {
      var own = el.value.replace(/^\s+|\s+$/g, '').length;
      var n = own || (el.getAttribute('placeholder') || '').length;
      out.textContent = own || !n ? tx('count', '{n} из {max} знаков', { n: n, max: max }) : tx('countAuto', '{n} из {max} знаков — текст сайта', { n: n, max: max });
      out.className = 'count' + (n > max ? ' is-long' : '');
    }
    el.addEventListener('input', update);
    update();
  });
})();
