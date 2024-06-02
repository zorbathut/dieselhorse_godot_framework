
import build_utils
import multiprocessing
import os
import psutil
import shutil
import util

util.cwdhack()

def run():
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
            "target=editor",
            "module_mono_enabled=yes",
            "debug_symbols=yes",
            f"precision={build_utils.get_float_precision()}",
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
           f"--precision={build_utils.get_float_precision()}",
        ], check=True, cwd="godot", env=build_utils.get_env())

    # Set up our fake universal link
    # We append .exe to it because Windows wants it and nothing else minds.
    universal_editor_path = "godot/bin/godot.universal.editor.double.x86_64.mono.exe"
    if os.path.exists(universal_editor_path):
        os.remove(universal_editor_path)
    
    util.platformswitch(
        linux = lambda: os.symlink(os.path.abspath(os.path.join("godot", util.godot_bin())), universal_editor_path),
        
        # This can be made faster by using a shortcut or mklink, but that's tough
        windows = lambda: shutil.copyfile(os.path.join("godot", util.godot_bin()), universal_editor_path),
    )()

    # Ramp priority back up for the editor itself.
    if util.platformswitch(linux = False, windows = True):
        proc.nice(psutil.NORMAL_PRIORITY_CLASS)

if __name__ == '__main__':
    run()
