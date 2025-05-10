
import argparse
import shutil
import sys
import util

util.cwdhack()

if not sys.platform.startswith("linux"):
    print("Currently Linux-only (though may not be hard to port)")
    raise

parser = argparse.ArgumentParser()
parser.add_argument("--commit", required = True)
args = parser.parse_args()

if util.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output = True).stdout.decode().strip() != "dev":
    print("Error: Not on dev branch (this is probably fixable but it'll take some work)")
    sys.exit(1)

util.run([
        "git",
        "clone",
        ".",
        "update_godot",
    ], check=True)

util.run([
        "git",
        "checkout",
        "thirdparty_godot",
    ], cwd = "update_godot", check=True)

util.run([
        "git",
        "clone",
        "--depth", "1",
        "--branch", args.commit,
        "https://github.com/godotengine/godot.git",
        "update_godot_engine",
    ], check=True)

util.run([
        "git",
        "checkout",
        args.commit,
    ], cwd = "update_godot_engine", check=True)

shutil.rmtree("update_godot/godot")
shutil.copytree("update_godot_engine", "update_godot/godot")

util.run([
        "git",
        "add",
        "-f",
        ".",
    ], cwd = "update_godot", check=True)

util.run([
        "git",
        "commit",
        "-m",
        f"Godot {args.commit}"
    ], cwd = "update_godot", check=True)

util.run([
        "git",
        "checkout",
        "dev",
    ], cwd = "update_godot", check=True)

if util.run([
        "git",
        "merge",
        "thirdparty_godot",
    ], cwd = "update_godot").returncode != 0:

    input("Merge conflicts; fix, commit, then hit enter")

util.run([
        "git",
        "fetch",
        "update_godot",
        "thirdparty_godot",
    ], check=True)

util.run([
        "git",
        "branch",
        "-f",
        "thirdparty_godot",
        "FETCH_HEAD",
    ], check=True)

util.run([
        "git",
        "fetch",
        "update_godot",
        "dev",
    ], check=True)

util.run([
        "git",
        "merge",
        "FETCH_HEAD",
        "--no-commit",
    ], check=True)

shutil.rmtree("update_godot")
shutil.rmtree("update_godot_engine")
