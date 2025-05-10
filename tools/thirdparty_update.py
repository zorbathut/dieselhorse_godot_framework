import argparse
import json
import os
import shutil
import sys
import util

util.cwdhack()

if not sys.platform.startswith("linux"):
    print("Currently Linux-only (though may not be hard to port)")
    raise

# Load the configuration file
CONFIG_FILE = "tools/thirdparty_update_config.json"

def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file '{CONFIG_FILE}' not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in configuration file '{CONFIG_FILE}'.")
        sys.exit(1)

def print_available_types(config):
    print("Available update types:")
    for slug, details in config.items():
        print(f"  {slug} - {details.get('description', 'No description')}")

parser = argparse.ArgumentParser()
parser.add_argument("--commit", required=True, help="Commit, tag, or branch to update to")
parser.add_argument("--type", required=False, help="Update type (from configuration file)")
args = parser.parse_args()

config = load_config()

# If type not provided, show available types and exit
if not args.type:
    print("Error: Update type (--type) not specified.")
    print_available_types(config)
    sys.exit(1)

# Check if the selected type exists in the configuration
if args.type not in config:
    print(f"Error: Update type '{args.type}' not found in configuration.")
    print_available_types(config)
    sys.exit(1)

# Get the configuration for the selected update type
update_config = config[args.type]
target_dir = update_config["target_dir"]
repo_url = update_config["repo_url"]
branch_name = update_config.get("branch_name", f"thirdparty_{args.type}")

print(f"Updating {args.type} to commit {args.commit}")

if util.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True).stdout.decode().strip() != "dev":
    print("Error: Not on dev branch (this is probably fixable but it'll take some work)")
    sys.exit(1)

work_dir = f"update_{args.type}"
parent_dir = f"{work_dir}_parent"

util.run([
        "git",
        "clone",
        ".",
        work_dir,
    ], check=True)

util.run([
        "git",
        "checkout",
        branch_name,
    ], cwd=work_dir, check=True)

util.run([
        "git",
        "clone",
        "--depth", "1",
        "--branch", args.commit,
        repo_url,
        parent_dir,
    ], check=True)

util.run([
        "git",
        "checkout",
        args.commit,
    ], cwd=parent_dir, check=True)

# Remove the old directory and replace with the new one
if os.path.exists(f"{work_dir}/{target_dir}"):
    shutil.rmtree(f"{work_dir}/{target_dir}")
shutil.copytree(parent_dir, f"{work_dir}/{target_dir}")

util.run([
        "git",
        "add",
        "-f",
        ".",
    ], cwd=work_dir, check=True)

util.run([
        "git",
        "commit",
        "-m",
        f"{args.type.capitalize()} {args.commit}"
    ], cwd=work_dir, check=True)

util.run([
        "git",
        "checkout",
        "dev",
    ], cwd=work_dir, check=True)

if util.run([
        "git",
        "merge",
        branch_name,
    ], cwd=work_dir).returncode != 0:

    input(f"Merge conflicts; fix, commit, then hit enter")

util.run([
        "git",
        "fetch",
        work_dir,
        branch_name,
    ], check=True)

util.run([
        "git",
        "branch",
        "-f",
        branch_name,
        "FETCH_HEAD",
    ], check=True)

util.run([
        "git",
        "fetch",
        work_dir,
        "dev",
    ], check=True)

util.run([
        "git",
        "merge",
        "FETCH_HEAD",
        "--no-commit",
    ], check=True)

# Cleanup
shutil.rmtree(work_dir)
shutil.rmtree(parent_dir)

print(f"Successfully updated {args.type} to {args.commit}")

