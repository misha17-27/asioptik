#!/usr/bin/env python3
"""Архивы для хостинга из текущего коммита репозитория.

    python3 build_zips.py [папка для архивов]        по умолчанию — текущая папка

    asioptik-site.zip     установка: содержимое site/ целиком, файлы лежат в корне архива
    asioptik-update.zip   обновление: то же без install.php — распаковывается поверх работающего сайта

Оба архива собирает сам git (git archive), и это важно. Такой архив не несёт в себе прав доступа к файлам,
поэтому при распаковке на хостинге файлы получают обычные права (644) и веб-сервер может их читать. Архив,
пересобранный другой программой, может молча записать права «только владелец» (600): после распаковки сервер
не прочитает .htaccess и ответит «Forbidden» на любой адрес сайта. Так уже случилось однажды, поэтому в конце
скрипт проверяет права в обоих архивах и останавливается, если они не те.
"""
import os, pathlib, subprocess, sys, tempfile, zipfile

ROOT = pathlib.Path(__file__).resolve().parent
OUT = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else pathlib.Path.cwd()
HTACCESS = ['.htaccess', 'admin/.htaccess', 'app/.htaccess', 'storage/.htaccess', 'uploads/.htaccess']


def git(*args, env=None):
    r = subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True, text=True, env=env)
    if r.returncode != 0:
        sys.exit(f'git {" ".join(args)}: {r.stderr.strip()}')
    return r.stdout.strip()


def check(path, installer):
    """Останавливает сборку, если архив на хостинге распакуется не так, как нужно."""
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        if bad: sys.exit(f'{path.name}: повреждён файл {bad}')
        names = z.namelist()
        for it in z.infolist():
            mode = (it.external_attr >> 16) & 0o777
            need = 0o755 if it.is_dir() else 0o644
            # прав нет вовсе (так пишет git) — хостинг поставит обычные; если права записаны, их должно хватать серверу
            if mode and mode & need != need:
                sys.exit(f'{path.name}: у {it.filename} записаны права {oct(mode)} — после распаковки веб-сервер не прочитает файл')
    # кроме страниц и скриптов сайта — библиотека карты филиалов: без неё на «Контактах» не будет меток
    for n in HTACCESS + ['index.php', 'admin/index.php', 'assets/js/app.js', 'assets/css/app.css', 'assets/vendor/leaflet/leaflet.js', 'assets/vendor/leaflet/leaflet.css']:
        if n not in names: sys.exit(f'{path.name}: нет файла {n}')
    if ('install.php' in names) != installer:
        sys.exit(f'{path.name}: install.php ' + ('должен быть в архиве' if installer else 'не должен попадать в архив обновления'))
    if any(n.startswith(('storage/config', 'storage/sessions/', 'uploads/')) and not n.endswith(('/', '.htaccess', '.gitkeep')) for n in names):
        sys.exit(f'{path.name}: в архив попали данные работающего сайта')
    return len(names)


if git('status', '--porcelain', '--', 'site'):
    sys.exit('В site/ есть незакоммиченные правки: архивы собираются из коммита, сначала сделайте коммит.')
OUT.mkdir(parents=True, exist_ok=True)
site_zip, update_zip = OUT / 'asioptik-site.zip', OUT / 'asioptik-update.zip'
git('archive', '--format=zip', '-o', str(site_zip), 'HEAD:site')
# для обновления — то же дерево без установщика: временный индекс git, сам репозиторий не меняется
with tempfile.TemporaryDirectory() as tmp:
    env = dict(os.environ, GIT_INDEX_FILE=str(pathlib.Path(tmp) / 'index'))
    git('read-tree', 'HEAD:site', env=env)
    git('update-index', '--force-remove', 'install.php', env=env)
    tree = git('write-tree', env=env)
git('archive', '--format=zip', '-o', str(update_zip), tree)
head = git('log', '-1', '--format=%h %s')
print(f'коммит {head}')
print(f'{site_zip}: {check(site_zip, True)} записей, установка')
print(f'{update_zip}: {check(update_zip, False)} записей, обновление (без install.php)')
