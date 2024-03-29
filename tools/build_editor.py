
import multiprocessing
import os
import psutil
import shutil
import subprocess
import sys
import util

util.cwdhack()

def run():
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
            "target=editor",
            "module_mono_enabled=yes",
            "debug_symbols=yes",
            f"precision={double_precision and 'double' or 'single'}",
        ], check=True, cwd="godot")
    
    # Generate Mono glue files.
    util.run([
            util.godot_bin(),
            "--headless",
            "--generate-mono-glue", "./modules/mono/glue",
        ], check=True, cwd="godot")
    
    # Build NuGet packages.
    util.run([
           "python",
           "./modules/mono/build_scripts/build_assemblies.py",
           "--godot-output-dir", "./bin",
           f"--precision={double_precision and 'double' or 'single'}",
        ], check=True, cwd="godot")

    # Ramp priority back up for the editor itself.
    if util.platformswitch(linux = False, windows = True):
        proc.nice(psutil.NORMAL_PRIORITY_CLASS)

if __name__ == '__main__':
    run()
