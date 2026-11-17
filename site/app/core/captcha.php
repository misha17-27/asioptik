<?php
/* Проверка «не робот» (Cloudflare Turnstile). Ключи и места проверки задаются в админ-панели, раздел «Безопасность».
   Проверка начинает действовать только после пробной проверки там же: неверным ключом нельзя закрыть себе вход. */
declare(strict_types=1);

const TURNSTILE_ORIGIN = 'https://challenges.cloudflare.com';
const TURNSTILE_SCRIPT = TURNSTILE_ORIGIN . '/turnstile/v0/api.js';

/** Настройка «turnstile»: ключи, где проверять, пройдена ли пробная проверка и последняя неисправность. */
function captcha_cfg(bool $fresh = false): array
{
    static $c = null;
    if ($c !== null && !$fresh) return $c;
    $s = setting('turnstile', []);
    if (!is_array($s)) $s = [];
    $str = function ($v): string {
        return is_string($v) ? trim($v) : '';
    };
    return $c = [
        'site' => $str($s['site'] ?? ''), 'secret' => $str($s['secret'] ?? ''),
        'login' => !empty($s['login']), 'forms' => !empty($s['forms']), 'ok' => !empty($s['ok']),
        'checked' => $str($s['checked'] ?? ''), 'fault' => $str($s['fault'] ?? ''), 'fault_at' => $str($s['fault_at'] ?? ''),
    ];
}

/** Запасной выключатель: строка 'captcha' => false в storage/config.php отключает проверку, если с ней не получается войти. */
function captcha_allowed(): bool
{
    $c = config();
    return !is_array($c) || !array_key_exists('captcha', $c) || $c['captcha'] !== false;
}

/** Включена ли проверка в настройках для этого места: 'login' — вход в админ-панель, 'forms' — заказ, заявка и сообщение с сайта. */
function captcha_ready(string $where): bool
{
    $c = captcha_cfg();
    return $c['ok'] && $c['site'] !== '' && $c['secret'] !== '' && !empty($c[$where]);
}

/** Действует ли проверка в этом месте прямо сейчас (включена в настройках и не отключена запасным выключателем). */
function captcha_on(string $where): bool
{
    return captcha_allowed() && captcha_ready($where);
}

/** Тестовые ключи Cloudflare пропускают всех: годятся для пробы на своём компьютере, но не для сайта. */
function captcha_dummy_key(string $key): bool
{
    return (bool) preg_match('~^[123]x0{20,}[A-Z]{2}$~', $key);
}

/** Адрес, по которому сервер проверяет ответ посетителя. Другой адрес задаётся только в storage/config.php (для проверок сайта). */
function captcha_verify_url(): string
{
    $c = config();
    $u = is_array($c) ? ($c['turnstile_verify'] ?? '') : '';
    return is_string($u) && preg_match('~^https?://~i', $u) ? $u : TURNSTILE_ORIGIN . '/turnstile/v0/siteverify';
}

/** Запрос с сервера: тело ответа или null, если связаться не удалось (нет cURL и запрещены исходящие запросы, истекло время). */
function http_post_form(string $url, array $fields, int $timeout = 8): ?string
{
    $body = http_build_query($fields);
    $head = ['Content-Type: application/x-www-form-urlencoded', 'Accept: application/json'];
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        if (!$ch) return null;
        curl_setopt_array($ch, [
            CURLOPT_POST => true, CURLOPT_POSTFIELDS => $body, CURLOPT_RETURNTRANSFER => true, CURLOPT_FOLLOWLOCATION => false,
            CURLOPT_CONNECTTIMEOUT => 5, CURLOPT_TIMEOUT => $timeout, CURLOPT_HTTPHEADER => $head,
        ]);
        $out = curl_exec($ch);
        unset($ch);
        return is_string($out) ? $out : null;
    }
    if (!filter_var(ini_get('allow_url_fopen'), FILTER_VALIDATE_BOOLEAN)) return null;
    $ctx = stream_context_create(['http' => ['method' => 'POST', 'header' => implode("\r\n", $head) . "\r\n", 'content' => $body, 'timeout' => $timeout, 'ignore_errors' => true, 'follow_location' => 0]]);
    $out = @file_get_contents($url, false, $ctx);
    return is_string($out) ? $out : null;
}

/**
 * Спрашивает у Cloudflare, прошёл ли посетитель проверку.
 * state: pass — прошёл; fail — не прошёл; error — проверить не удалось (нет связи или Cloudflare не принял секретный ключ).
 */
function captcha_verify(string $token, ?array $cfg = null): array
{
    $cfg = $cfg ?? captcha_cfg();
    // ответ посетителя — строка без пробелов не длиннее 2048 знаков; пустое и заведомо негодное даже не отправляем
    if (!preg_match('~^[\x21-\x7E]{10,2048}\z~', $token)) return ['state' => 'fail', 'codes' => ['missing-input-response']];
    $raw = http_post_form(captcha_verify_url(), ['secret' => (string) $cfg['secret'], 'response' => $token]);
    $j = is_string($raw) ? json_decode($raw, true) : null;
    if (!is_array($j) || !array_key_exists('success', $j)) return ['state' => 'error', 'codes' => [is_string($raw) ? 'bad-answer' : 'no-connection']];
    if ($j['success'] === true) return ['state' => 'pass', 'codes' => []];
    $codes = array_values(array_filter(is_array($j['error-codes'] ?? null) ? $j['error-codes'] : [], 'is_string'));
    // Секретный ключ посетитель подменить не может: если Cloudflare не принял ключ, неисправна настройка, а не посетитель
    $setup = (bool) array_intersect($codes, ['missing-input-secret', 'invalid-input-secret']);
    return ['state' => $setup ? 'error' : 'fail', 'codes' => $codes];
}

/**
 * Проверка для входа и для форм сайта. Если проверить не удалось, пропускаем: остаются пароль, предел попыток
 * и ключ страницы, а неисправность видна в разделе «Безопасность».
 */
function captcha_pass(string $token): bool
{
    $r = captcha_verify($token);
    if ($r['state'] === 'error') {
        captcha_fault($r['codes'][0] ?? 'no-connection');
        error_log('[asioptik] капча не сработала: ' . implode(', ', $r['codes']));
        return true;
    }
    if ($r['state'] === 'pass') captcha_fault('');
    return $r['state'] === 'pass';
}

/** Запоминает последнюю неисправность проверки (или снимает её). В базу пишет, только когда что-то изменилось. */
function captcha_fault(string $code): void
{
    $c = captcha_cfg();
    if ($c['fault'] === $code) return;
    $s = setting('turnstile', []);
    if (!is_array($s) || empty($s['site'])) return;
    if ($code === '') unset($s['fault'], $s['fault_at']);
    else {
        $s['fault'] = $code;
        $s['fault_at'] = now();
    }
    set_setting('turnstile', $s);
    captcha_cfg(true);
}
