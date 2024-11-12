
import argparse
import build_editor
import build_utils
import test
import util

util.cwdhack()

def run(dev):
    build_editor.run(dev)

    test.run()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Build editor")
    build_utils.decorate_argparse_with_dev(parser)
    args = parser.parse_args()

    run(args.dev)
