<?php
/* Язык интерфейса админ-панели: русский, азербайджанский или английский.
   Исходные строки в коде русские; переводы лежат в app/admin/lang/az.php и en.php: «русская строка» => «перевод».
   Строка без перевода показывается по-русски. На язык сайта для покупателей это не влияет. */
declare(strict_types=1);

const UI_LANGS = ['ru' => 'Русский', 'az' => 'Azərbaycan dili', 'en' => 'English'];

/** Язык интерфейса: выбран переключателем в админ-панели и запомнен в cookie ao_ui. */
function ui_lang(?string $set = null): string
{
    static $lang = null;
    if ($set !== null && isset(UI_LANGS[$set])) $lang = $set;
    if ($lang === null) {
        $c = $_COOKIE['ao_ui'] ?? '';
        $lang = is_string($c) && isset(UI_LANGS[$c]) ? $c : 'ru';
    }
    return $lang;
}

/** Словарь выбранного языка (для русского пустой). */
function ui_dict(): array
{
    static $all = [];
    $l = ui_lang();
    if ($l === 'ru') return [];
    if (!isset($all[$l])) {
        $file = APP . '/admin/lang/' . $l . '.php';
        $d = is_file($file) ? require $file : [];
        $all[$l] = is_array($d) ? $d : [];
    }
    return $all[$l];
}

/** Строка интерфейса на выбранном языке. В $vars — значения для слов в фигурных скобках: __('Запись {n} удалена.', ['n' => $number]). */
function __(string $ru, array $vars = []): string
{
    $s = ui_dict()[$ru] ?? $ru;
    if (!$vars) return $s;
    $map = [];
    foreach ($vars as $k => $v) $map['{' . $k . '}'] = (string) $v;
    return strtr($s, $map);
}

/**
 * Слово в нужной форме для числа: n__(5, 'товар', 'товара', 'товаров').
 * Перевод ищется по ключу «товар|товара|товаров»: для английского в нём две формы через черту (product|products), для азербайджанского одна.
 */
function n__(int $n, string $one, string $few, string $many): string
{
    $l = ui_lang();
    if ($l === 'ru') {
        $a = abs($n) % 100;
        $b = $a % 10;
        if ($a > 10 && $a < 20) return $many;
        if ($b === 1) return $one;
        return $b >= 2 && $b <= 4 ? $few : $many;
    }
    $forms = explode('|', __($one . '|' . $few . '|' . $many));
    if ($l === 'en' && count($forms) > 1) return abs($n) === 1 ? $forms[0] : $forms[1];
    return $forms[0];
}
