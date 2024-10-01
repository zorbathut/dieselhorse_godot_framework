
import os
import subprocess
import sys

# right now poetry doesn't let us set the project directory, so we need to find the right directory for scripts first
def cwdhack():
    while not os.path.exists("project"):
        # verify we haven't reached the root, including on windows
        if os.getcwd() == os.path.dirname(os.getcwd()):
            raise FileNotFoundError("Couldn't find project directory!")
        os.chdir("..")

def platformswitch(linux, windows, mac):
    if sys.platform.startswith("linux"):
        return linux
    elif sys.platform.startswith("win32"):
        return windows
    elif sys.platform.startswith("darwin"):
        return mac
    else:
        raise InvalidOperation("Unidentified OS :(")

def run(command, **kwargs):
    print("Executing: " + " ".join(command))

    # decorate our args
    platformargs = platformswitch(
        linux = {},
        windows = {},
        mac = {},
    )

    ourargs = {**platformargs, **kwargs}

    if platformswitch(linux = False, windows = True, mac = False) and "\\" in command[0] and "cwd" in ourargs:
        # windows, weirdly, evaluates the executable first, *then* cwd's
        # so if we have a relative executable name we need to decorate it with our cwd
        command[0] = os.path.join(ourargs["cwd"], command[0])

    # if you don't do this, it silently fails to pass parameters through
    # seriously how is subprocess such a mess
    if "shell" in ourargs and ourargs["shell"] == True:
        command = " ".join(command)

    return subprocess.run(command, **kwargs)

def godot_bin(dev):
    if dev:
        return platformswitch(
            linux = "bin/godot.linuxbsd.editor.dev.double.x86_64.mono",
            windows = "bin\\godot.windows.editor.dev.double.x86_64.mono.exe",
            mac = "bin/godot.macos.editor.dev.double.x86_64.mono")
    else:
        return platformswitch(
            linux = "bin/godot.linuxbsd.editor.double.x86_64.mono",
            windows = "bin\\godot.windows.editor.double.x86_64.mono.exe",
            mac = "bin/godot.macos.editor.double.x86_64.mono")
