 
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

def run():
    if util.platformswitch(linux = False, windows = True):
        print("This definitely won't work on Windows.")
        sys.exit(1)

    # need local editor infrastructure to exist for this
    build_editor.run()

    # this really shouldn't be redundant
    double_precision = True

    # kick priority down to make builds smoother
    # can't do this on linux unfortunately; shell out to a niced build_editor?
    if util.platformswitch(linux = False, windows = True):
        proc = psutil.Process(os.getpid())
        proc.nice(psutil.IDLE_PRIORITY_CLASS)

    platform = util.platformswitch(linux = "linuxbsd", windows = "windows")

    cores = multiprocessing.cpu_count()
    print(f"Running with {cores} cores")

    # Build the binary itself (yay this is no longer two-pass)
    util.run([
            "scons",
            "-j", f"{cores}",
            f"p={platform}",
            "target=template_release",
            "arch=x86_64",
            "production=yes",
            #"lto=full", # currently crashes    
            "module_mono_enabled=yes",
            "debug_symbols=yes",
            f"precision={double_precision and 'double' or 'single'}",
        ], check=True, cwd="godot", env=build_utils.get_env())

    # Generate Mono glue files.
    util.run([
            util.godot_bin(),
            "--headless",
            "--generate-mono-glue", "./modules/mono/glue",
        ], check=True, cwd="godot", env=build_utils.get_env())

    # Make necessary directory
    os.makedirs("godot/bin/GodotSharp/Tools/nupkgs", exist_ok=True)

    # Build NuGet packages.
    util.run([
            "python",
            "./modules/mono/build_scripts/build_assemblies.py",
            "--godot-output-dir", "./bin",
            f"--precision={double_precision and 'double' or 'single'}",
        ], check=True, cwd="godot", env=build_utils.get_env())

    # Clear and remake necessary directory
    if os.path.exists("deploy/linux"):
        shutil.rmtree("deploy/linux")
    os.makedirs("deploy/linux", exist_ok=True)

    # Run headless export
    util.run([
            f"godot/bin/godot.{platform}.editor.double.x86_64.mono",
            "--headless",
            "--path", "project",
            "--export-release", "linux",
            "../deploy/linux/moonskrive",
        ], check=True, env=build_utils.get_env())

    # Copy dec directory over
    shutil.copytree("project/dec", "deploy/linux/dec")

    # Ramp priority back up for the editor itself.
    if util.platformswitch(linux = False, windows = True):
        proc.nice(psutil.NORMAL_PRIORITY_CLASS)

if __name__ == '__main__':
    run()
