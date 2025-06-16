
import os
import util

def get_env():
    """Get the environment variables for the current platform."""
    env = os.environ.copy()
    env['GODOT_VERSION_STATUS'] = get_project_name()

    # use the build-environment path for Linux builds
    if "GODOT_SDK_LINUX_X86_64" in env:
        env["PATH"] = env["GODOT_SDK_LINUX_X86_64"] + "/bin" + ':' + env["PATH"]

    return env

# separate from the build profile because we need to pass this into the Mono glue generator as well
def get_float_precision():
    return "double"

def get_build_profile():
    return f"build_profile=../project/godot.build_profile.json"

def get_project_name():
    return "planefarer"

def get_project_version():
    # make sure to convert to an actual string
    return util.run(["git", "describe", "--tags", "--always", "--dirty"], check=True, capture_output=True).stdout.strip().decode("utf-8")

def decorate_argparse_with_dev(parser):
    parser.add_argument("--dev", action="store_true", default=False, help="Enable development mode")
