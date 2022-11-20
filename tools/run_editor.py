
import multiprocessing
import os
import psutil
import shutil
import subprocess
import sys
import util

util.cwdhack()

def run():
    util.subprocess_run_reporting(["godot/bin/godot.windows.opt.tools.x86_64.mono.exe", "project/project.godot"])

if __name__ == '__main__':
    run()
