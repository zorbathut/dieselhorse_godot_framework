@setlocal
@cd tools
%APPDATA%\pypoetry\venv\Scripts\poetry install
%APPDATA%\pypoetry\venv\Scripts\poetry run python run_editor.py
