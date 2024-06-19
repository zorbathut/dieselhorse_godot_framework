
import os
import pprint
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

    # decorate our args
    platformargs = platformswitch(
        linux = {},
        windows = {},
    )

    ourargs = {**platformargs, **kwargs}

    if platformswitch(linux = False, windows = True) and "\\" in command[0] and "cwd" in ourargs:
        # windows, weirdly, evaluates the executable first, *then* cwd's
        # so if we have a relative executable name we need to decorate it with our cwd
        command[0] = os.path.join(ourargs["cwd"], command[0])

    # if you don't do this, it silently fails to pass parameters through
    # seriously how is subprocess such a mess
    if "shell" in ourargs and ourargs["shell"] == True:
        command = " ".join(command)

    pprint.pprint(command, kwargs)
    return subprocess.run(command, **kwargs)

def godot_bin():
    return platformswitch(
        linux = "bin/godot.linuxbsd.editor.double.x86_64.mono",
        windows = "bin\\godot.windows.editor.double.x86_64.mono.exe")
