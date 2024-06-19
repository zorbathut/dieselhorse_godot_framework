
import os
import pprint

def get_env():
    """Get the environment variables for the current platform."""
    env = os.environ.copy()
    env['GODOT_VERSION_STATUS'] = 'moonskrive'

    # use the build-environment path for Linux builds
    print("GETENV RESULTS")
    pprint.pprint(env)
    if "GODOT_SDK_LINUX_X86_64" in env:
        print(f"Using Linux SDK path: {env["GODOT_SDK_LINUX_X86_64"]}")
        # print all files in the SDK directory
        print("Files in SDK directory:")
        for root, dirs, files in os.walk(env["GODOT_SDK_LINUX_X86_64"]):
            for file in files:
                print(os.path.join(root, file))

        env["PATH"] = env["GODOT_SDK_LINUX_X86_64"] + "/bin" + ':' + env["PATH"]
        print(f"New PATH: {env["PATH"]}")

    return env

def get_float_precision():
    #return "single"
    return "double"
