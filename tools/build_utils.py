
import os

def get_env():
    """Get the environment variables for the current platform."""
    env = os.environ.copy()
    env['GODOT_VERSION_STATUS'] = 'moonskrive'

    # use the build-environment path for Linux builds
    if "GODOT_SDK_LINUX_X86_64" in env:
        print(f"Using Linux SDK path: {env["GODOT_SDK_LINUX_X86_64"]}")
        env["PATH"] = env["GODOT_SDK_LINUX_X86_64"] + "/bin" + ':' + env["PATH"]

    return env

def get_float_precision():
    #return "single"
    return "double"

def get_project_name():
    return "moonskrive"
