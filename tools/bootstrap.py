
import os
import sys

# this runs from main directory so we need to specify stuff
import tools.util

def execute(token, args = [], shell = False):
    # Explicitly unbuffer the output
    # this is really hacky and comes from https://stackoverflow.com/questions/107705/disable-output-buffering
    # I am not totally sold on it
    # wish you could just tell python "hey stop buffering kthx"
    class Unbuffered(object):
        def __init__(self, stream):
            self.stream = stream
        def write(self, data):
            self.stream.write(data)
            self.stream.flush()
        def writelines(self, datas):
            self.stream.writelines(datas)
            self.stream.flush()
        def __getattr__(self, attr):
            return getattr(self.stream, attr)
    sys.stdout = Unbuffered(sys.stdout)
    
    poetry_options = [
        shutil.which("poetry"),
        os.path.expandvars("%APPDATA%/pypoetry/venv/Scripts/poetry.exe"),   # windows default install location
        "C:/Users/runneradmin/.local/bin/poetry.exe", # snok/install-poetry
    ]

    poetry = None
    for option in poetry_options:
        if option is None:
            continue

        if os.path.exists(option):
            poetry = option
            break
    
    if poetry is None:
        print("Poetry not found!")
        sys.exit(1)

    print(f"Poetry found at {poetry}")
    
    tools.util.run([
            poetry,
            "install",
            "--no-root",
        ], check=True, cwd="tools")
       
    print("Poetry install complete")
    
    tools.util.run([
            poetry,
            "run",
            "python",
            "-u", # unbuffered to avoid problems with output ordering on jenkins
            f"{token}.py",
        ] + args, check=True, cwd="tools", shell=shell)
