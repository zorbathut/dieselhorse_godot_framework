
import argparse
import requests
import shutil
import subprocess
import sys
import util

util.cwdhack()

if not sys.platform.startswith("linux"):
    print("Currently Linux-only (though may not be hard to port)")
    raise

parser = argparse.ArgumentParser()
parser.add_argument("--repo", required = True)
parser.add_argument("--commit", required = True)
args = parser.parse_args()


def get_commit_message(repo, commit):
    """
    Retrieve the commit message from GitHub given a repo and a commit.
    """
    api_url = f"https://api.github.com/repos/{repo}/commits/{commit}"
    response = requests.get(api_url)

    if response.status_code == 200:
        commit_data = response.json()
        return commit_data['commit']['message']
    else:
        print(f"Failed to retrieve commit message: {response.status_code}")
        return None


patch_url = f"https://github.com/{args.repo}/commit/{args.commit}.patch"
response = requests.get(patch_url)

if response.status_code != 200:
    print(f"Failed to download patch: {response.status_code}")
    exit(1)

# Change to the target directory
subprocess.run(['patch', '-p1', '--no-backup-if-mismatch'], input=response.text, text=True, check=True, cwd="godot")
subprocess.run(["git", "add", "godot"])
subprocess.run(["git", "commit", "-m", get_commit_message(args.repo, args.commit)], cwd="godot")
print("Patch applied successfully.")
