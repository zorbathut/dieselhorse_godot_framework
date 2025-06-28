
import build_utils
import containerize
import os
import shutil
import util

util.cwdhack()

def build_deploy(target):
    """Build and deploy for a specific target."""
    
    containerize.run(target, "deploy", [f"--target={target}"])

def run():
    # wipe deploy directory entirely
    shutil.rmtree("deploy", ignore_errors = True)

    # Build and deploy for Linux
    build_deploy('linux')

    # Build and deploy for Windows
    build_deploy('windows')

if __name__ == '__main__':
    run()
