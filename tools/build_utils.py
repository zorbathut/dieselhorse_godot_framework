
import os
import util

def get_env():
    """Get the environment variables for the current platform."""
    env = os.environ.copy()
    env['GODOT_VERSION_STATUS'] = 'tsoh'

    # use the build-environment path for Linux builds
    if "GODOT_SDK_LINUX_X86_64" in env:
        env["PATH"] = env["GODOT_SDK_LINUX_X86_64"] + "/bin" + ':' + env["PATH"]

    return env

def get_float_precision():
    #return "single"
    return "double"

def get_project_name():
    return "tsoh"

def get_project_version():
    # make sure to convert to an actual string
    return util.run(["git", "describe", "--tags", "--always", "--dirty"], check=True, capture_output=True).stdout.strip().decode("utf-8")