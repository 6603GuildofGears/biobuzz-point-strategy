@echo off
cd /d "%~dp0"
set N=%1
if "%N%"=="" set N=4000
py -3 -m biobuzz simulate --matches %N% --out output
echo Open output\report.html
