
import subprocess

import build_editor

import cwdhack
cwdhack.cwdhack()

def run():
    build_editor.run()
    
    subprocess.run(["godot/bin/godot.windows.opt.tools.x86_64.mono.exe", "project/project.godot"])

if __name__ == '__main__':
    run()
