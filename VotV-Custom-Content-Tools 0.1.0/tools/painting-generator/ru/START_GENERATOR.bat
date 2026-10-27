@echo off
setlocal
cd /d "%~dp0"

REM Use the Windows Python launcher first, then fall back to python.
set "PYTHON_CMD=py"
%PYTHON_CMD% -c "import sys; print(sys.version)" >nul 2>&1
if errorlevel 1 (
    set "PYTHON_CMD=python"
    %PYTHON_CMD% -c "import sys; print(sys.version)" >nul 2>&1
)
%PYTHON_CMD% -c "import sys; assert sys.version_info >= (3,9)" >nul 2>&1
if errorlevel 1 goto no_python

%PYTHON_CMD% -c "import PIL" >nul 2>&1
if errorlevel 1 goto install_pillow
goto run_app

:install_pillow
echo Pillow was not found. Attempting to install it...
%PYTHON_CMD% -m pip install --user pillow
if errorlevel 1 goto install_failed

:run_app
%PYTHON_CMD% painting_generator.py
if errorlevel 1 goto app_failed
exit /b 0

:no_python
echo Python 3.9 or newer was not found.
echo Install Python from https://www.python.org/downloads/
echo During installation, enable "Add Python to PATH".
pause
exit /b 1

:install_failed
echo Could not install Pillow.
echo Try running this command in Command Prompt:
echo %PYTHON_CMD% -m pip install --user pillow
pause
exit /b 1

:app_failed
echo The application closed with an error. Check the message above.
pause
exit /b 1
