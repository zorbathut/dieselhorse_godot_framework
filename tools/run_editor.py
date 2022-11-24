
import multiprocessing
import os
import psutil
import shutil
import subprocess
import sys
import util

util.cwdhack()

def run():
    util.run([
        "godot/" + util.godot_bin(),
        "project/project.godot"
    ])

if __name__ == '__main__':
    run()
