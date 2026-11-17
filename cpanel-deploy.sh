#!/bin/sh
# Выкладка сайта в папку на хостинге. Вызывается из .cpanel.yml, когда в cPanel нажимают «Deploy HEAD Commit»
# (Git Version Control → Manage → Pull or Deploy). Можно запустить и руками из папки репозитория:
#
#     sh cpanel-deploy.sh /home/пользователь/public_html/asioptik
#
# Что делает: копирует в указанную папку содержимое site/ — и только его.
# Чего не делает: ничего не удаляет (кроме install.php на уже установленном сайте) и ничего не трогает за
# пределами указанной папки. Настройки (storage/config.php), база данных и фото (uploads/) остаются как были.
#
# Защита от ошибки в пути: если в указанной папке уже лежит другой сайт, а не Asioptik, выкладка останавливается
# и ничего не меняет. Так нельзя по ошибке затереть основной сайт домена, указав его папку вместо папки Asioptik.
set -eu

DEST=${1:-}
SRC=$(cd "$(dirname "$0")" && pwd)/site

stop() { echo "Выкладка остановлена, ничего не изменено: $1" >&2; exit 1; }

[ -n "$DEST" ] || stop "не указана папка сайта"
case "$DEST" in /*) ;; *) stop "папка сайта должна быть указана полным путём, а получено «$DEST»" ;; esac
[ -f "$SRC/index.php" ] && [ -f "$SRC/app/site/site.php" ] || stop "рядом со скриптом нет папки site/ с сайтом"

# В папке что-то есть, но это не Asioptik (нет его файла app/site/site.php) — значит, там чужой сайт
if [ -d "$DEST" ] && [ -n "$(ls -A "$DEST" 2>/dev/null)" ] && [ ! -f "$DEST/app/site/site.php" ]; then
    stop "в папке $DEST лежит другой сайт"
fi

mkdir -p "$DEST"
cp -R "$SRC/." "$DEST/"

# Установщик нужен только до установки: на работающем сайте он не остаётся
if [ -f "$DEST/storage/config.php" ]; then rm -f "$DEST/install.php"; fi

# Веб-сервер работает от другого пользователя, чем владелец файлов: файлам сайта нужны права 644, папкам 755.
# Иначе сервер не прочитает .htaccess и ответит «Forbidden» на любой адрес.
chmod -R u=rwX,go=rX "$DEST/admin" "$DEST/app" "$DEST/assets"
chmod 644 "$DEST/.htaccess" "$DEST/.user.ini" "$DEST/index.php" "$DEST/favicon.ico" "$DEST/storage/.htaccess" "$DEST/uploads/.htaccess"

echo "Сайт выложен в $DEST"
