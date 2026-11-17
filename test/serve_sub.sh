#!/bin/sh
# Стенд «сайт в подпапке чужого сайта», как на хостинге с cPanel: http://127.0.0.1:8772/asioptik/
# Корень — «основной сайт» со своим .htaccess и своими папками admin/ и assets/; Asioptik лежит в подпапке
# asioptik/ чистой копией, как после распаковки архива для хостинга. Тот же каталог отдаётся ещё и как корень
# отдельного сайта на http://127.0.0.1:8773/ — так проверяется будущий перенос на свой домен без перекладывания файлов.
# Перед запуском должен работать основной стенд (sh test/serve.sh): база данных у них общая.
# Запуск:  sh test/serve_sub.sh [путь к asioptik-site.zip]     Остановка:  sh test/serve_sub.sh stop
ROOT=$(cd "$(dirname "$0")/.." && pwd)
RUN=/tmp/asioptik-sub
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
  echo "остановлено"; exit 0
fi
stop_pid "$RUN/httpd.pid" apache2 && sleep 1
rm -f "$RUN/httpd.pid"
ZIP=${1:-}
mkdir -p "$RUN/logs" "$RUN/root/admin" "$RUN/root/assets"
# сайт распаковывается заново: чистая папка, как после загрузки архива в файловый менеджер
if [ -d "$RUN/root/asioptik" ]; then mv "$RUN/root/asioptik" "$RUN/old-$(date +%s)"; fi
mkdir -p "$RUN/root/asioptik"
if [ -n "$ZIP" ]; then (cd "$RUN/root/asioptik" && unzip -q "$ZIP")
else
  # без архива — копия папки site/ в том виде, в каком она попадает в архив: без всего, что появляется после установки
  rsync -a --exclude='/storage/config.php' --exclude='/storage/*.sqlite' --exclude='/storage/sessions/' \
    --exclude='/storage/cache/*' --exclude='/storage/logs/*' --exclude='/uploads/*/' "$ROOT/site/" "$RUN/root/asioptik/"
  touch "$RUN/root/asioptik/storage/cache/.gitkeep" "$RUN/root/asioptik/storage/logs/.gitkeep"
fi
# «основной сайт»: свои страницы, свои admin/ и assets/, все прочие адреса уходят в его index.php
printf '<?php header("X-Main-Site: 1"); echo "MAIN SITE: " . htmlspecialchars($_SERVER["REQUEST_URI"]);\n' > "$RUN/root/index.php"
printf '<?php header("X-Main-Site: 1"); echo "MAIN ADMIN";\n' > "$RUN/root/admin/index.php"
printf 'body{color:red}\n' > "$RUN/root/assets/main.css"
cat > "$RUN/root/.htaccess" <<HT
RewriteEngine On
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^ index.php [L]

# Заголовки безопасности основного сайта действуют на весь домен, значит и на папку Asioptik. Такие стоят на
# настоящем хостинге (mguliyev.com): строгая политика без встроенных скриптов, чужих шрифтов и картинок.
# MAIN_HEADERS=always — тот же набор через «Header always set», MAIN_HEADERS=none — без заголовков.
<IfModule mod_headers.c>
MAINHDR Content-Security-Policy "default-src 'self'; script-src 'self' https://challenges.cloudflare.com; frame-src https://challenges.cloudflare.com; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data:; media-src 'self'; connect-src 'self' https://challenges.cloudflare.com; form-action 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'"
MAINHDR Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()"
MAINHDR Referrer-Policy "strict-origin-when-cross-origin"
MAINHDR X-Frame-Options "SAMEORIGIN"
MAINHDR X-Content-Type-Options "nosniff"
MAINHDR Strict-Transport-Security "max-age=31536000; includeSubDomains"
</IfModule>
HT
case "${MAIN_HEADERS:-set}" in
  always) sed -i 's/^MAINHDR /Header always set /' "$RUN/root/.htaccess" ;;
  none)   sed -i '/^MAINHDR /d' "$RUN/root/.htaccess" ;;
  *)      sed -i 's/^MAINHDR /Header set /' "$RUN/root/.htaccess" ;;
esac
chown -R www-data:www-data "$RUN/root"
mariadb --socket=/tmp/mysql-run/mysqld.sock -uroot -e "DROP DATABASE IF EXISTS asioptik_sub; CREATE DATABASE asioptik_sub CHARACTER SET utf8mb4; GRANT ALL ON asioptik_sub.* TO 'aotest'@'127.0.0.1';"
cat > "$RUN/httpd.conf" <<CONF
ServerRoot "$RUN"
PidFile $RUN/httpd.pid
Listen 127.0.0.1:8772
Listen 127.0.0.1:8773
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
<FilesMatch "\.php$">
    SetHandler application/x-httpd-php
</FilesMatch>
DirectoryIndex index.php index.html
<Directory "$RUN/root">
    AllowOverride All
    Require all granted
</Directory>
<VirtualHost 127.0.0.1:8772>
    DocumentRoot "$RUN/root"
</VirtualHost>
<VirtualHost 127.0.0.1:8773>
    DocumentRoot "$RUN/root/asioptik"
</VirtualHost>
CONF
apache2 -f "$RUN/httpd.conf" -k start
sleep 1
echo "сайт в подпапке:      http://127.0.0.1:8772/asioptik/"
echo "та же папка корнем:   http://127.0.0.1:8773/"
