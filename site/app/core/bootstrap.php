<?php
/* Общая часть сайта и админ-панели: пути, настройки подключения, мелкие помощники. */
declare(strict_types=1);

define('ROOT', dirname(__DIR__, 2));
define('APP', ROOT . '/app');
define('STORAGE', ROOT . '/storage');
define('UPLOADS', ROOT . '/uploads');

error_reporting(E_ALL);
ini_set('display_errors', '0');
ini_set('log_errors', '1');
ini_set('error_log', STORAGE . '/logs/php-errors.log');
ini_set('session.use_strict_mode', '1');
ini_set('session.use_only_cookies', '1');
mb_internal_encoding('UTF-8');
date_default_timezone_set('Asia/Baku');
header_remove('X-Powered-By');   // версию PHP посетителям не сообщаем

set_exception_handler(function (Throwable $e): void {
    error_log('[asioptik] ' . get_class($e) . ': ' . $e->getMessage() . ' in ' . $e->getFile() . ':' . $e->getLine());
    if (!headers_sent()) {
        http_response_code(500);
        header('Content-Type: text/html; charset=utf-8');
    }
    echo '<!doctype html><meta charset="utf-8"><title>Ошибка</title><p style="font:16px/1.5 sans-serif;margin:40px">Сайт временно недоступен. Обновите страницу через минуту.</p>';
    exit;
});

/** Настройки из storage/config.php (их записывает установщик); null, пока сайт не установлен. */
function config(): ?array
{
    static $c = false;
    if ($c === false) {
        $f = STORAGE . '/config.php';
        $c = is_file($f) ? (require $f) : null;
        if (!is_array($c)) $c = null;
    }
    return $c;
}

function e($s): string
{
    return htmlspecialchars((string) $s, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

/** Путь к корню сайта в адресе, со слэшем на конце: «/» или, например, «/shop/». */
function base_path(): string
{
    static $b = null;
    if ($b !== null) return $b;
    $c = config();
    if (!empty($c['base'])) return $b = '/' . trim((string) $c['base'], '/') . (trim((string) $c['base'], '/') === '' ? '' : '/');
    $doc = isset($_SERVER['DOCUMENT_ROOT']) ? realpath((string) $_SERVER['DOCUMENT_ROOT']) : false;
    $root = realpath(ROOT);
    if ($doc && $root && strpos($root, $doc) === 0) {
        $rel = trim(str_replace('\\', '/', substr($root, strlen($doc))), '/');
        return $b = $rel === '' ? '/' : '/' . $rel . '/';
    }
    $dir = str_replace('\\', '/', dirname((string) ($_SERVER['SCRIPT_NAME'] ?? '/')));
    if (defined('IN_ADMIN')) $dir = str_replace('\\', '/', dirname($dir));
    return $b = rtrim($dir, '/') . '/';
}

function is_https(): bool
{
    return (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off')
        || (($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') === 'https')
        || ((string) ($_SERVER['SERVER_PORT'] ?? '') === '443');
}

/** Сайт открыт на своём компьютере (проверка перед загрузкой на хостинг). */
function is_local(): bool
{
    $host = strtolower((string) preg_replace('~:\d+$~', '', (string) ($_SERVER['HTTP_HOST'] ?? '')));
    return in_array($host, ['localhost', '127.0.0.1', '[::1]'], true) || (bool) preg_match('~\.(localhost|test)$~', $host);
}

/** Домен для сравнения адресов: строчными буквами, без «www.», номера порта и точки на конце. */
function host_key(string $host): string
{
    $h = rtrim((string) preg_replace('~:\d+$~', '', strtolower(trim($host))), '.');
    return (string) preg_replace('~^www\.~', '', $h);
}

/** Пароль, который подбирают первым: из частых, из одинаковых знаков или совпадает с логином. */
function weak_password(string $pass, string $login = ''): bool
{
    $p = mb_strtolower($pass);
    $common = ['12345678', '123456789', '1234567890', '87654321', '11111111', '00000000', 'password', 'password1', 'password123', 'qwertyui', 'qwertyuiop',
        'qwerty123', '1q2w3e4r', '1qaz2wsx', 'abc12345', 'iloveyou', 'admin123', 'admin1234', 'adminadmin', 'asioptik', 'asioptik1', 'asioptik123', 'optika123'];
    if (in_array($p, $common, true)) return true;
    if (count(array_unique(mb_str_split($p))) < 4) return true;
    return $login !== '' && $p === mb_strtolower($login);
}

function origin(): string
{
    return (is_https() ? 'https' : 'http') . '://' . ($_SERVER['HTTP_HOST'] ?? 'localhost');
}

/** Адрес посетителя хранится только в виде необратимого отпечатка. */
function client_ip_hash(): string
{
    $c = config();
    return hash('sha256', ($c['secret'] ?? '') . '|' . ($_SERVER['REMOTE_ADDR'] ?? ''));
}

function redirect(string $url, int $code = 302): void
{
    header('Location: ' . $url, true, $code);
    exit;
}

function json_out($data, int $code = 200): void
{
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
    exit;
}

function now(): string
{
    return date('Y-m-d H:i:s');
}

function to_json($v): string
{
    return json_encode($v, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
}

/** Значение по ключу с точками: dget($a, 'banner.text'). */
function dget(array $a, string $key, $default = null)
{
    foreach (explode('.', $key) as $k) {
        if (!is_array($a) || !array_key_exists($k, $a)) return $default;
        $a = $a[$k];
    }
    return $a;
}

function dset(array &$a, string $key, $value): void
{
    $ref = &$a;
    foreach (explode('.', $key) as $k) {
        if (!isset($ref[$k]) || !is_array($ref[$k])) $ref[$k] = [];
        $ref = &$ref[$k];
    }
    $ref = $value;
}

function dunset(array &$a, string $key): void
{
    $parts = explode('.', $key);
    $last = array_pop($parts);
    $ref = &$a;
    foreach ($parts as $k) {
        if (!isset($ref[$k]) || !is_array($ref[$k])) return;
        $ref = &$ref[$k];
    }
    unset($ref[$last]);
}

require APP . '/core/i18n.php';
require APP . '/core/db.php';
require APP . '/core/store.php';
require APP . '/core/captcha.php';
