
import argparse
import build_utils
import multiprocessing
import os
import psutil
import shutil
import util

util.cwdhack()

def run(dev):
    # kick priority down to make builds smoother
    # can't do this on linux unfortunately; shell out to a niced build_editor?
    if util.platformswitch(linux = False, windows = True, mac = False):
        proc = psutil.Process(os.getpid())
        proc.nice(psutil.IDLE_PRIORITY_CLASS)

    platform = util.platformswitch(linux = "linuxbsd", windows = "windows", mac = "osx")

    cores = multiprocessing.cpu_count()
    print(f"Running with {cores} cores")
    
    # Clear out old generated binaries
    shutil.rmtree("godot/bin", ignore_errors=True)

    # Build the binary itself (yay this is no longer two-pass)
    util.run([
            "scons",
            "-j", f"{cores}",
            f"p={platform}",
            "target=editor"]
            + (["dev_build=yes"] if dev else []) +
            [f"precision={build_utils.get_float_precision()}",
            build_utils.get_build_profile()
        ], check=True, cwd="godot", env=build_utils.get_env())
    
    # Generate Mono glue files.
    util.run([
            util.godot_bin(dev),
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
           f"--precision={build_utils.get_float_precision()}",
        ], check=True, cwd="godot", env=build_utils.get_env())

    # Set up our fake universal link
    # We append .exe to it because Windows wants it and nothing else minds.
    universal_editor_path = "godot/bin/godot.universal.editor.exe"
    if os.path.exists(universal_editor_path):
        os.remove(universal_editor_path)
    
    util.platformswitch(
        linux = lambda: os.symlink(os.path.abspath(os.path.join("godot", util.godot_bin(dev))), universal_editor_path),
        mac = lambda: os.symlink(os.path.abspath(os.path.join("godot", util.godot_bin(dev))), universal_editor_path),
        
        # This can be made faster by using a shortcut or mklink, but that's tough
        windows = lambda: shutil.copyfile(os.path.join("godot", util.godot_bin(dev)), universal_editor_path),
    )()

    # Ramp priority back up for the editor itself.
    if util.platformswitch(linux = False, windows = True, mac = False):
        proc.nice(psutil.NORMAL_PRIORITY_CLASS)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Build editor")
    build_utils.decorate_argparse_with_dev(parser)
    args = parser.parse_args()

    run(args.dev)
