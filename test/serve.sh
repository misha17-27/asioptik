#!/bin/sh
# Тестовый стенд для проверок: MariaDB на порту 3307 и Apache с PHP на http://127.0.0.1:8771 (корень — папка site/),
# плюс простой сервер на http://127.0.0.1:8765 для сайта одним файлом (dist/).
# Нужны пакеты: mariadb-server apache2 libapache2-mod-php php-mysql php-gd php-mbstring php-sqlite3
# Запуск:  sh test/serve.sh        Остановка:  sh test/serve.sh stop
ROOT=$(cd "$(dirname "$0")/.." && pwd)
RUN=/tmp/asioptik-test
PHPMOD=$(ls /usr/lib/apache2/modules/libphp8*.so 2>/dev/null | tail -1)

# Останавливает процесс из файла с его номером, только если это та самая программа: после перезагрузки
# под старым номером может работать уже другой процесс.
stop_pid() {
  [ -f "$1" ] || return 0
  pid=$(cat "$1" 2>/dev/null)
  [ -n "$pid" ] && [ "$(cat "/proc/$pid/comm" 2>/dev/null)" = "$2" ] && kill "$pid" 2>/dev/null
  return 0
}

if [ "$1" = "stop" ]; then
  stop_pid "$RUN/httpd.pid" apache2
  stop_pid "$RUN/mysqld.pid" mariadbd
  stop_pid "$RUN/static.pid" python3
  echo "остановлено"; exit 0
fi

mkdir -p "$RUN/logs" "$RUN/mysql-run"
# --- база данных: только для проверок, пароль ни от чего настоящего не подходит
if [ ! -d "$RUN/mysql-data/mysql" ]; then
  mariadb-install-db --user=root --datadir="$RUN/mysql-data" >/dev/null 2>&1
fi
if ! mariadb --socket=/tmp/mysql-run/mysqld.sock -uroot -e "SELECT 1" >/dev/null 2>&1; then
  mkdir -p /tmp/mysql-run
  nohup mariadbd --user=root --datadir="$RUN/mysql-data" --socket=/tmp/mysql-run/mysqld.sock --pid-file="$RUN/mysqld.pid" \
    --port=3307 --bind-address=127.0.0.1 >"$RUN/logs/mysql.log" 2>&1 &
  for i in 1 2 3 4 5 6 7 8 9 10; do
    mariadb --socket=/tmp/mysql-run/mysqld.sock -uroot -e "SELECT 1" >/dev/null 2>&1 && break; sleep 1
  done
fi
mariadb --socket=/tmp/mysql-run/mysqld.sock -uroot -e "CREATE DATABASE IF NOT EXISTS asioptik_test CHARACTER SET utf8mb4;
  CREATE USER IF NOT EXISTS 'aotest'@'127.0.0.1' IDENTIFIED BY 'test-only-local';
  GRANT ALL ON asioptik_test.* TO 'aotest'@'127.0.0.1';"

# --- Apache с PHP: корень сайта — папка site/
cat > "$RUN/httpd.conf" <<CONF
ServerRoot "$RUN"
PidFile $RUN/httpd.pid
Listen 127.0.0.1:8771
ServerName localhost
User www-data
Group www-data
LoadModule mpm_prefork_module /usr/lib/apache2/modules/mod_mpm_prefork.so
LoadModule authz_core_module /usr/lib/apache2/modules/mod_authz_core.so
LoadModule dir_module /usr/lib/apache2/modules/mod_dir.so
LoadModule mime_module /usr/lib/apache2/modules/mod_mime.so
LoadModule rewrite_module /usr/lib/apache2/modules/mod_rewrite.so
LoadModule headers_module /usr/lib/apache2/modules/mod_headers.so
LoadModule php_module $PHPMOD
TypesConfig /etc/mime.types
ErrorLog $RUN/logs/error.log
LogLevel warn
StartServers 2
MaxRequestWorkers 8
DocumentRoot "$ROOT/site"
<Directory "$ROOT/site">
    AllowOverride All
    Require all granted
</Directory>
<FilesMatch "\.php$">
    SetHandler application/x-httpd-php
</FilesMatch>
DirectoryIndex index.php index.html
CONF
chown -R www-data:www-data "$ROOT/site/storage" "$ROOT/site/uploads"
stop_pid "$RUN/httpd.pid" apache2 && sleep 1
rm -f "$RUN/httpd.pid"
apache2 -f "$RUN/httpd.conf" -k start

# --- сайт одним файлом
stop_pid "$RUN/static.pid" python3
(cd "$ROOT" && nohup python3 -m http.server 8765 --bind 127.0.0.1 >"$RUN/logs/static.log" 2>&1 & echo $! > "$RUN/static.pid")
sleep 1
echo "сайт на PHP:        http://127.0.0.1:8771/   (чистая установка: python3 test/php_reset.py)"
echo "сайт одним файлом:  http://127.0.0.1:8765/dist/optika-4-lupa.html"
