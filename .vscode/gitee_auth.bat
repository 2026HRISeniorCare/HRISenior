@echo off
chcp 65001 >nul
echo ============================================
echo  Gitee Submodule Auth Setup
echo  A browser window will open for Gitee login
echo ============================================
echo.

cd /d C:\Users\25453\esp-idf

echo [1/2] Triggering Gitee authentication...
echo Please login to Gitee in the browser window...
git ls-remote https://gitee.com/EspressifSystems/esp-lwip.git
if %errorlevel% neq 0 (
    echo.
    echo [FAIL] Authentication failed
    pause
    exit /b 1
)
echo [OK] Authenticated

echo.
echo [2/2] Pulling all submodules (~500MB, may take several minutes)...
git submodule update --init --recursive

if %errorlevel% equ 0 (
    echo.
    echo ============================================
    echo   SUCCESS - All submodules pulled!
    echo ============================================
) else (
    echo.
    echo WARNING: Some submodules failed to pull
)
pause
