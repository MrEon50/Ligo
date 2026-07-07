@echo off
REM ================================================================
REM LIGO Framework — Clean All __pycache__ Folders
REM Recursively removes all __pycache__ directories in the project.
REM ================================================================

setlocal enabledelayedexpansion

echo Cleaning __pycache__ folders in: %cd%
echo.

for /d /r %%i in (__pycache__) do (
    echo Removing: %%i
    rmdir /s /q "%%i" 2>nul
)

echo.
echo Done!
