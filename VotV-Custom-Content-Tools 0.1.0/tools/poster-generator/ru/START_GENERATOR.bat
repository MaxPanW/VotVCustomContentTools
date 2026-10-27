@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if not errorlevel 1 (
    set "PYTHON=py"
) else (
    set "PYTHON=python"
)

%PYTHON% -c "import PIL" >nul 2>&1
if errorlevel 1 (
    echo Pillow not found. Installing it now...
    %PYTHON% -m pip install --user Pillow
    if errorlevel 1 (
        echo.
        echo Could not install Pillow. Make sure Python and pip are installed.
        pause
        exit /b 1
    )
)

%PYTHON% poster_square_generator.py
if errorlevel 1 pause
endlocal
