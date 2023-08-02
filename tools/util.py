
import os
import subprocess
import sys

# right now poetry doesn't let us set the project directory, so we need to find the right directory for scripts first
def cwdhack():
    while not os.path.exists("README.txt"):
        os.chdir("..")

def platformswitch(linux, windows):
    if sys.platform.startswith("linux"):
        return linux
    elif sys.platform.startswith("win32"):
        return windows
    else:
        raise InvalidOperation("Unidentified OS :(")

def run(command, **kwargs):
    print("Executing: " + " ".join(command))

    # if you don't do this, it silently fails to pass parameters through
    if "shell" in kwargs and kwargs["shell"] == True:
        command = " ".join(command)

    return platformswitch(
        linux = lambda: subprocess.run(command, **kwargs),
        windows = lambda: subprocess.run(command, shell = True, **kwargs))()

def godot_bin():
    return platformswitch(
        linux = "bin/godot.linuxbsd.editor.x86_64.mono",
        windows = "bin\\godot.windows.editor.x86_64.mono.exe")
