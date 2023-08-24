import os
import subprocess
import sys
import tempfile

def generate_patch(commit_id, patch_dir):
    command = ["git", "format-patch", "-1", commit_id, "-o", patch_dir]
    subprocess.run(command)
    # Get the name of the patch file
    patch_name = os.listdir(patch_dir)[0]
    return os.path.join(patch_dir, patch_name)

def apply_patch(patch_path, target_repo):
    command = ["git", "apply", "--reject", "-p2", patch_path]
    result = subprocess.run(command, cwd=target_repo)
    # If there were rejections, result.returncode will be non-zero
    return result.returncode == 0

def main(commit_ids, target_repo):
    # Create a temporary directory to store patches
    with tempfile.TemporaryDirectory() as patch_dir:
        # Generate and apply patches
        for commit_id in commit_ids:
            patch_path = generate_patch(commit_id, patch_dir)
            print(f"Generated patch for commit ID {commit_id}")

            # Apply the patch
            success = apply_patch(patch_path, target_repo)
            if not success:
                print(f"Merge conflict or error occurred while applying patch for commit ID {commit_id}")
                input("Press Enter to continue after manually resolving any conflicts...")
            else:
                print(f"Successfully applied patch for commit ID {commit_id}")

        print("All patches have been processed.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python script_name.py TARGET_REPO commit_id_1 commit_id_2 ...")
    else:
        target_repo = sys.argv[1]
        commit_ids = sys.argv[2:]
        main(commit_ids, target_repo)
