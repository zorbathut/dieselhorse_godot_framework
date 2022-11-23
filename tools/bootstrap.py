
# this runs from main directory so we need to specify stuff
import tools.util

def execute(token):
    tools.util.subprocess_run_reporting([
            "%APPDATA%/pypoetry/venv/Scripts/poetry",
            "install",
        ], shell=True, check=True, cwd="tools")
    
    tools.util.subprocess_run_reporting([
            "%APPDATA%/pypoetry/venv/Scripts/poetry",
            "run",
            "python",
            f"{token}.py",
        ], shell=True, check=True, cwd="tools")    

