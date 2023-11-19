
import sys

# this runs from main directory so we need to specify stuff
import tools.util

def execute(token, args = [], shell = False):
    poetry = tools.util.platformswitch(
        linux = "poetry",
        windows = "%APPDATA%/pypoetry/venv/Scripts/poetry")
    
    tools.util.run([
            poetry,
            "install",
            "--no-root",
        ], check=True, cwd="tools")
    
    tools.util.run([
            poetry,
            "run",
            "python",
            f"{token}.py",
        ] + args, check=True, cwd="tools", shell=shell)
