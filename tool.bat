#!/bin/sh
: '
@echo off
REM Windows part
py "%~dp0\tools\bootstrap.py" tool %*
exit /b
'
# Shell script part
/usr/bin/env python3 "$(dirname "$0")/tools/bootstrap.py" "$@"
