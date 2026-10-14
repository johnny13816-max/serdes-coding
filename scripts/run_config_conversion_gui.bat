@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"
set "PYTHON_EXE=%PROJECT_ROOT%\.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Project Python was not found:
    echo         %PYTHON_EXE%
    echo.
    echo Recreate the environment at ^<project_root^>\.venv before launching the GUI.
    pause
    exit /b 1
)

set "PYTHONPATH=%PROJECT_ROOT%\src;%PYTHONPATH%"
cd /d "%PROJECT_ROOT%"

"%PYTHON_EXE%" -m serdes_coding.interfaces.com_config_conversion_gui %*
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo [ERROR] COM config conversion GUI exited with code %EXIT_CODE%.
    pause
)

exit /b %EXIT_CODE%
