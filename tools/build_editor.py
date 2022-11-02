
import multiprocessing
import os
import psutil
import shutil
import subprocess
import sys

import cwdhack
cwdhack.cwdhack()

def run():
    # kick priority down to make builds smoother
    proc = psutil.Process(os.getpid())
    proc.nice(psutil.IDLE_PRIORITY_CLASS)

    cores = multiprocessing.cpu_count()
    print(f"Running with {cores} cores")
    
    # Wipe out the GodotNuGetFallbackFolder because Godot does not properly update it
    fallbackdir = os.path.expandvars("%APPDATA%/Godot/mono/GodotNuGetFallbackFolder")
    if os.path.exists(fallbackdir):
        shutil.rmtree(fallbackdir)
        os.makedirs(fallbackdir)
    
    subprocess.run([
            "scons",
            "-j", f"{cores}",
            "p=windows",
            "target=release_debug",
            "tools=yes",
            "module_mono_enabled=yes",
        ], shell=True, check=True, cwd="godot")
        
    subprocess.run([
            "bin\godot.windows.opt.tools.x86_64.mono.exe",
            "--headless",
            "--generate-mono-glue", "./modules/mono/glue",
        ], shell=True, check=True, cwd="godot")

    nugetdir = os.path.expandvars("%APPDATA%/NuGetLocal")
    if not os.path.exists(nugetdir):
        os.makedirs(nugetdir)
    subprocess.run([
            "dotnet", "nuget",
            "add", "source", nugetdir,
            "--name", "NuGetLocal",
        ], shell=True)  # not checking, it'll fail on the seond run if we do
    
    subprocess.run([
           "python",
           "./modules/mono/build_scripts/build_assemblies.py",
           "--godot-output-dir", "./bin",
           "--push-nupkgs-local", nugetdir,
        ], shell=True, check=True, cwd="godot")

    # priority back up
    proc.nice(psutil.NORMAL_PRIORITY_CLASS)

if __name__ == '__main__':
    run()
