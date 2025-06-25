
import argparse
import build_utils
import os
import util

util.cwdhack()

def run(dev):
    util.run([
        os.path.join("godot", "bin", "godot.universal.editor.exe"),
        "project/project.godot"
    ])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Build editor")
    build_utils.decorate_argparse_with_dev(parser)
    args = parser.parse_args()

    run(args.dev)
