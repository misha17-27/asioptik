@echo off
chcp 65001 >nul
title Asioptik - local
rem Просмотр сайта на своём компьютере: встроенный сервер PHP, без хостинга.
rem Сайт откроется в браузере по адресу http://127.0.0.1:8088/
cd /d "%~dp0"
set "PORT=8088"
set "PHP=php"
where php >nul 2>nul
if not errorlevel 1 goto run
if exist "%USERPROFILE%\.config\herd\bin\php.bat" set "PHP=%USERPROFILE%\.config\herd\bin\php.bat" & goto run
if exist "C:\xampp\php\php.exe" set "PHP=C:\xampp\php\php.exe" & goto run
if exist "C:\php\php.exe" set "PHP=C:\php\php.exe" & goto run
echo.
echo  PHP не найден. Установите PHP 8 (например, Laravel Herd или XAMPP)
echo  и запустите этот файл ещё раз.
echo.
pause
exit /b 1

:run
echo.
echo  Сайт:          http://127.0.0.1:%PORT%/
echo  Админ-панель:  http://127.0.0.1:%PORT%/admin/
echo.
echo  При первом запуске откроется установка: оставьте галочку
echo  "Проверка на своём компьютере" и придумайте пароль.
echo  Чтобы остановить сайт, закройте это окно.
echo.
start "" /min cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:%PORT%/"
call "%PHP%" -S 127.0.0.1:%PORT% -t site local\router.php
echo.
echo  Сервер остановлен. Если выше написано "Failed to listen", порт %PORT% занят:
echo  откройте этот файл в Блокноте и замените 8088 в строке PORT на другое число.
pause
