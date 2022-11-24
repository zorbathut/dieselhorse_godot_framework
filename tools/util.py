
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

    return platformswitch(
        linux = lambda: subprocess.run(command, **kwargs),
        windows = lambda: subprocess.run(command, shell = True, **kwargs))()

def godot_bin():
    return platformswitch(
        linux = "bin/godot.linuxbsd.opt.tools.x86_64.mono",
        windows = "bin/godot.windows.opt.tools.x86_64.mono.exe")