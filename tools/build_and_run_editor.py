
import build_editor
import run_editor
import subprocess
import util

util.cwdhack()

def run():
    build_editor.run()
    
    run_editor.run()

if __name__ == '__main__':
    run()
