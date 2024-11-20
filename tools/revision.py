
import argparse 
import build_editor
import build_utils
import multiprocessing
import os
import psutil
import shutil
import subprocess
import sys
import util

util.cwdhack()

import sys
import subprocess
import tempfile
import os
from datetime import datetime

def get_last_tag():
    """Get the most recent git tag, or None if no tags exist."""
    try:
        return subprocess.check_output(
            ["git", "describe", "--tags", "--abbrev=0"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except subprocess.CalledProcessError:
        return None

def get_release_notes(last_tag):
    """Get all commit messages since the last tag."""
    git_log_cmd = ["git", "log", "--format=%B"]
    if last_tag:
        git_log_cmd.append(f"{last_tag}..HEAD")
    
    commits = subprocess.check_output(git_log_cmd).decode()
    
    # Extract lines starting with "RN: " and remove the prefix
    release_notes = []
    for line in commits.split('\n'):
        if line.startswith('RN: '):
            release_notes.append(line[4:].strip())
    
    return sorted(set(release_notes))  # Remove duplicates and sort

def prepend_to_changelog(version, notes):
    """Prepend new release notes to CHANGELOG.md"""
    today = datetime.now().strftime('%Y-%m-%d')
    new_content = f"# {version} ({today})\n\n"
    for note in notes:
        new_content += f"* {note}\n"
    new_content += "\n"
    
    try:
        with open('CHANGELOG.md', 'r') as f:
            existing_content = f.read()
    except FileNotFoundError:
        existing_content = ""
    
    with open('CHANGELOG.md', 'w') as f:
        f.write(new_content + existing_content)

def open_editor(filename):
    """Open Git's preferred editor and wait for it to close."""
    try:
        # Use git var to get Git's preferred editor
        editor = subprocess.check_output(
            ["git", "var", "GIT_EDITOR"],
            stderr=subprocess.PIPE
        ).decode().strip()
    except subprocess.CalledProcessError:
        # Fallback to system default if git var fails
        editor = os.environ.get('EDITOR', 'vim')
    
    subprocess.call(editor.split() + [filename])

def create_git_tag(version):
    """Create and push a new git tag."""
    subprocess.check_call(["git", "add", "CHANGELOG.md"])
    subprocess.check_call(["git", "commit", "-m", f"Release {version}"])
    subprocess.check_call(["git", "tag", "-a", version, "-m", f"Release {version}"])

def run():
    if len(sys.argv) != 2:
        print("Usage: revision.py <version>")
        print("Example: revision.py v1.2.3")
        sys.exit(1)
    
    version = sys.argv[1]
    if not version.startswith('v'):
        version = 'v' + version
    
    # Get the last tag
    last_tag = get_last_tag()
    print(f"Last tag: {last_tag}")
    
    # Get release notes from commits
    release_notes = get_release_notes(last_tag)
    if not release_notes:
        print("No release notes found in commits (looking for lines starting with 'RN: ')")
        sys.exit(1)
    
    # Update CHANGELOG.md
    prepend_to_changelog(version, release_notes)
    print(f"Added {len(release_notes)} release notes to CHANGELOG.md")
    
    # Open editor for manual review
    open_editor('CHANGELOG.md')
    
    # Confirm with user
    response = input("Would you like to commit and tag this release? [y/N] ")
    if response.lower() != 'y':
        print("Aborting release.")
        sys.exit(0)
    
    # Create git tag
    try:
        create_git_tag(version)
        print(f"Successfully created release {version}")
    except subprocess.CalledProcessError as e:
        print(f"Error creating git tag: {e}")
        sys.exit(1)

if __name__ == '__main__':
    run()
