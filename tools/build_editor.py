
import multiprocessing
import os
import psutil
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
    
    subprocess.run([
            "scons",
            "-j", f"{cores}",
            "p=windows",
            "tools=yes",
            "module_mono_enabled=yes",
            "mono_glue=no",
        ], shell=True, check=True, cwd="godot")
        
    subprocess.run([
            "bin\godot.windows.tools.x86_64.mono.exe",
            "--generate-mono-glue", "modules/mono/glue",
        ], shell=True, check=True, cwd="godot")

    subprocess.run([
            "scons",
            "-j", f"{cores}",
            "p=windows",
            "target=release_debug",
            "tools=yes",
            "module_mono_enabled=yes",
        ], shell=True, check=True, cwd="godot")

    # priority back up
    proc.nice(psutil.NORMAL_PRIORITY_CLASS)

if __name__ == '__main__':
    run()
