@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title VotV PMX Converter - Batch Mode

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYRUN=py -3"
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        set "PYRUN=python"
    ) else (
        echo [ERROR] Python 3 was not found.
        echo Install Python from https://www.python.org/downloads/windows/
        echo During setup, enable "Add Python to PATH".
        pause
        exit /b 1
    )
)

%PYRUN% -c "import PIL" >nul 2>nul
if not %errorlevel%==0 (
    echo Pillow is missing. Trying to install it automatically...
    %PYRUN% -m pip install --user pillow
    if not %errorlevel%==0 (
        echo [ERROR] Pillow installation failed. Check your Internet connection and Python pip.
        pause
        exit /b 1
    )
)

echo.
echo === VOTV PMX batch converter ===
echo With no arguments: converts every .pmx inside the input folder.
echo You can also drag one or more .pmx files onto this .bat file.
echo.
%PYRUN% convert_all.py %*
set "EXITCODE=%errorlevel%"
echo.
if "%EXITCODE%"=="0" (
    echo Done. Check the printer in VotV and logs folder if needed.
) else (
    echo Finished with warnings/errors. Read logs\conversion-*.log
)
pause
exit /b %EXITCODE%
