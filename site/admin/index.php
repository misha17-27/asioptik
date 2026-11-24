<?php
/* Админ-панель Asioptik. */
define('IN_ADMIN', true);
require dirname(__DIR__) . '/app/core/bootstrap.php';
require APP . '/site/site.php';
require APP . '/admin/schema.php';
require APP . '/admin/views.php';
require APP . '/admin/pages.php';
require APP . '/admin/security.php';
require APP . '/admin/users.php';
require APP . '/admin/media.php';
require APP . '/admin/mail.php';
require APP . '/admin/admin.php';
admin_run();
