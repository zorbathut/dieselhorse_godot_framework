
import argparse 
import build_editor
import build_utils
import multiprocessing
import os
import psutil
import shutil
import subprocess
import sys
import util

util.cwdhack()

parser = argparse.ArgumentParser()
parser.add_argument("--target", required = True, choices=["linux", "windows"])
args = parser.parse_args()

def run():
    if util.platformswitch(linux = False, windows = True):
        print("This definitely won't work on Windows.")
        sys.exit(1)

    # we do this both to build the mono glue files and to build the editor that we can use to run the deploy code
    # it's possible we should build this separately in our jenkins build, then copy it over
    build_editor.run()

    cores = multiprocessing.cpu_count()
    print(f"Running with {cores} cores")

    # Build the binary itself (yay this is no longer two-pass)
    util.run([
            "scons",
            "-j", f"{cores}",
            f"p={args.target}",
            "target=template_release",
            "arch=x86_64",
            "production=yes",
            "module_mono_enabled=yes",
            "debug_symbols=yes",
            f"precision={build_utils.get_float_precision()}", 
        ], check=True, cwd="godot", env=build_utils.get_env())

    # Mono glue files already exist from us building the editor
    # Don't need to build them a second time
    # (but do need to build the editor)
    
    # Make necessary directory
    os.makedirs("godot/bin/GodotSharp/Tools/nupkgs", exist_ok=True)

    # Build NuGet packages.
    util.run([
            "python",
            "./modules/mono/build_scripts/build_assemblies.py",
            "--godot-output-dir", "./bin",
            f"--precision={build_utils.get_float_precision()}",
        ], check=True, cwd="godot", env=build_utils.get_env())

    # Clear and remake necessary directory
    deploydir = f"deploy/{args.target}"
    if os.path.exists(deploydir):
        shutil.rmtree(deploydir)
    os.makedirs(deploydir, exist_ok=True)

    # Run headless export
    util.run([
            "godot/" + util.godot_bin(),
            "--headless",
            "--path", "project",
            "--export-release", args.target,
            f"../{deploydir}/{build_utils.get_project_name()}",
        ], check=True, env=build_utils.get_env())

    # Copy dec directory over
    shutil.copytree("project/dec", f"{deploydir}/dec")

    if util.platformswitch(linux = True, windows = False):
        # All the debug info is shoved in the executable, so let's pull that out
        util.run([
                "strip",
                f"{deploydir}/{build_utils.get_project_name()}",
            ], check=True)
    
    if util.platformswitch(linux = False, windows = True):
        # Needs an .exe suffix
        os.rename(f"{deploydir}/{build_utils.get_project_name()}", f"{deploydir}/{build_utils.get_project_name()}.exe")

if __name__ == '__main__':
    run()
