@ECHO OFF

SETLOCAL EnableExtensions

SET parent=%~dp0
rem PUSHD "%parent%"
CD /D "%parent%"
CD ..

rem SET script=%~dpn0.py
SET script=elasticsearch_setup.py

set PYTHON_DIR=C:/Python311
set PATH=%PYTHON_DIR%;%PYTHON_DIR%/Scripts;%PYTHON_DIR%/Library/bin;%PATH%
SET PYTHONPATH=../src;../src/third_party;%PYTHONPATH%

python.exe "%parent%\%script%" %*

PAUSE

ENDLOCAL

EXIT /B 0
