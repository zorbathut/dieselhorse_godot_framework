
import multiprocessing
import os
import psutil
import shutil
import subprocess
import sys
import util

util.cwdhack()

def run():
    # kick priority down to make builds smoother
    # can't do this on linux, currently disabled
    #proc = psutil.Process(os.getpid())
    #proc.nice(psutil.IDLE_PRIORITY_CLASS)

    platform = util.platformswitch(linux = "linuxbsd", windows = "windows")

    cores = multiprocessing.cpu_count()
    print(f"Running with {cores} cores")
    
    # Wipe out the GodotNuGetFallbackFolder because Godot does not properly update it
    fallbackdir = os.path.expandvars("%APPDATA%/Godot/mono/GodotNuGetFallbackFolder")
    if os.path.exists(fallbackdir):
        shutil.rmtree(fallbackdir)
        os.makedirs(fallbackdir)
    
    util.run([
            "scons",
            "-j", f"{cores}",
            f"p={platform}",
            "target=editor",
            "tools=yes",
            "module_mono_enabled=yes",
        ], check=True, cwd="godot")
        
    util.run([
            util.godot_bin(),
            "--headless",
            "--generate-mono-glue", "./modules/mono/glue",
        ], check=True, cwd="godot")

    nugetdir = util.platformswitch(linux = os.path.expanduser("~/.nuget/NuGetLocal"), windows = os.path.expandvars("%APPDATA%/NuGetLocal"))
    if not os.path.exists(nugetdir):
        print(f"Making {nugetdir}")
        os.makedirs(nugetdir)
    
    util.run([
            "dotnet", "nuget",
            "add", "source", nugetdir,
            "--name", "NuGetLocal",
        ])  # not checking, it'll fail on the seond run if we do
    
    util.run([
           "python",
           "./modules/mono/build_scripts/build_assemblies.py",
           "--godot-output-dir", "./bin",
           "--push-nupkgs-local", nugetdir,
        ], check=True, cwd="godot")

    # priority back up
    #proc.nice(psutil.NORMAL_PRIORITY_CLASS)

if __name__ == '__main__':
    run()
