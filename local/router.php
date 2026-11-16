<?php
/* Просмотр сайта на своём компьютере встроенным сервером PHP, без Apache и хостинга.
   Запуск из папки проекта:  php -S 127.0.0.1:8088 -t site local/router.php
   (на Windows это делает файл start-local.bat). Этот файл повторяет правила из site/.htaccess:
   адреса страниц ведут в index.php, служебные папки закрыты. На хостинг его загружать не нужно. */
if (PHP_SAPI !== 'cli-server') {
    http_response_code(404);
    exit;
}
$site = dirname(__DIR__) . DIRECTORY_SEPARATOR . 'site';
$path = rawurldecode((string) (parse_url((string) ($_SERVER['REQUEST_URI'] ?? '/'), PHP_URL_PATH) ?: '/'));
$deny = function (int $code = 403): void {
    http_response_code($code);
    header('Content-Type: text/plain; charset=utf-8');
    echo $code === 403 ? "403 Forbidden\n" : "404 Not Found\n";
    exit;
};

// как на хостинге: служебные папки, скрытые файлы и файлы настроек из браузера не открываются
if (strpos($path, "\0") !== false || strpos($path, '..') !== false) $deny();
if (preg_match('~^/(app|storage)(/|$)~i', $path)) $deny();
if (preg_match('~(^|/)\.(?!well-known/)~', $path)) $deny();
if (preg_match('~\.(md|json|log|sql|sqlite|sh|py|lock|bak|ini)$~i', $path)) $deny();

$file = $site . str_replace('/', DIRECTORY_SEPARATOR, $path);
if (preg_match('~^/uploads(/|$)~i', $path)) {   // в папке с загруженными фото отдаются только картинки
    if (is_file($file) && preg_match('~\.(jpe?g|png|webp)$~i', $path) && !preg_match('~\.(php\d?|phtml|phar|pht|s?html?|js|svg)\.~i', $path)) return false;
    $deny(is_file($file) || is_dir($file) ? 403 : 404);
}
if (is_file($file) && !preg_match('~\.php$~i', $path)) return false;   // стили, скрипты, значок сайта — отдаёт сам сервер
if (is_dir($file) && !preg_match('~^/(admin/?)?$~', $path)) $deny();     // списки файлов в папках не показываем

if ($path === '/admin') {
    header('Location: /admin/' . (($q = (string) ($_SERVER['QUERY_STRING'] ?? '')) !== '' ? '?' . $q : ''), true, 301);
    exit;
}
$script = preg_match('~^/admin/(index\.php)?$~', $path) ? '/admin/index.php' : ($path === '/install.php' && is_file($site . '/install.php') ? '/install.php' : '/index.php');
$_SERVER['SCRIPT_NAME'] = $script;
$_SERVER['SCRIPT_FILENAME'] = $site . str_replace('/', DIRECTORY_SEPARATOR, $script);
$_SERVER['PHP_SELF'] = $script;
chdir(dirname($_SERVER['SCRIPT_FILENAME']));
require $_SERVER['SCRIPT_FILENAME'];
