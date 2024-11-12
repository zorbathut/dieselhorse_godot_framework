
import argparse
import build_utils
import os
import util

util.cwdhack()

def run():
    util.run([
        "dotnet",
        "test",
    ], check=True)

if __name__ == '__main__':
    run()
