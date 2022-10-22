@setlocal
@cd tools
%APPDATA%\pypoetry\venv\Scripts\poetry install
%APPDATA%\pypoetry\venv\Scripts\poetry run python build_and_run_editor.py
