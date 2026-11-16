<?php
/* База данных: подключение и таблицы. Основная база — MySQL; SQLite поддерживается для проверки сайта на своём компьютере. */
declare(strict_types=1);

function db_connect(array $d): PDO
{
    $opt = [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES => false,
    ];
    if (($d['driver'] ?? 'mysql') === 'sqlite') {
        return new PDO('sqlite:' . $d['path'], null, null, $opt);
    }
    $dsn = 'mysql:host=' . $d['host'] . (empty($d['port']) ? '' : ';port=' . (int) $d['port']) . ';dbname=' . $d['name'] . ';charset=utf8mb4';
    return new PDO($dsn, (string) $d['user'], (string) $d['pass'], $opt);
}

function db(): PDO
{
    static $pdo = null;
    if ($pdo) return $pdo;
    $c = config();
    if (!$c) throw new RuntimeException('Сайт ещё не установлен');
    return $pdo = db_connect($c['db']);
}

function q(string $sql, array $args = []): PDOStatement
{
    $st = db()->prepare($sql);
    $st->execute($args);
    return $st;
}

/** Создаёт таблицы, если их ещё нет. Все таблицы с приставкой ao_, чтобы не мешать другим сайтам в той же базе. */
function db_schema(PDO $pdo): void
{
    $mysql = $pdo->getAttribute(PDO::ATTR_DRIVER_NAME) === 'mysql';
    $id = $mysql ? 'INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY' : 'INTEGER PRIMARY KEY AUTOINCREMENT';
    $end = $mysql ? ' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci' : '';
    $text = $mysql ? 'MEDIUMTEXT' : 'TEXT';
    $sql = [
        "CREATE TABLE IF NOT EXISTS ao_settings (name VARCHAR(64) NOT NULL PRIMARY KEY, value $text NOT NULL)$end",
        "CREATE TABLE IF NOT EXISTS ao_items (id $id, type VARCHAR(20) NOT NULL, slug VARCHAR(80) NOT NULL, position INT NOT NULL DEFAULT 0, active TINYINT NOT NULL DEFAULT 1, data $text NOT NULL, updated_at DATETIME NOT NULL)$end",
        "CREATE TABLE IF NOT EXISTS ao_orders (id $id, number VARCHAR(24) NOT NULL, kind VARCHAR(12) NOT NULL, status VARCHAR(12) NOT NULL DEFAULT 'new', created_at DATETIME NOT NULL, name VARCHAR(120) NOT NULL DEFAULT '', phone VARCHAR(40) NOT NULL DEFAULT '', total DECIMAL(10,2) NULL, lang VARCHAR(5) NOT NULL DEFAULT '', data $text NOT NULL, ip_hash CHAR(64) NOT NULL DEFAULT '')$end",
        "CREATE TABLE IF NOT EXISTS ao_users (id $id, login VARCHAR(60) NOT NULL, pass_hash VARCHAR(255) NOT NULL, created_at DATETIME NOT NULL)$end",
        "CREATE TABLE IF NOT EXISTS ao_logins (id $id, ip_hash CHAR(64) NOT NULL, created_at DATETIME NOT NULL)$end",
    ];
    foreach ($sql as $s) $pdo->exec($s);
    $indexes = [
        'ao_items_type_slug' => 'CREATE UNIQUE INDEX ao_items_type_slug ON ao_items (type, slug)',
        'ao_items_type_pos' => 'CREATE INDEX ao_items_type_pos ON ao_items (type, position)',
        'ao_orders_created' => 'CREATE INDEX ao_orders_created ON ao_orders (created_at)',
        'ao_orders_ip' => 'CREATE INDEX ao_orders_ip ON ao_orders (ip_hash, created_at)',
        'ao_users_login' => 'CREATE UNIQUE INDEX ao_users_login ON ao_users (login)',
        'ao_logins_ip' => 'CREATE INDEX ao_logins_ip ON ao_logins (ip_hash, created_at)',
    ];
    foreach ($indexes as $name => $s) {
        try {
            $pdo->exec($s);
        } catch (PDOException $e) {
            // индекс уже есть — это не ошибка
        }
    }
}
