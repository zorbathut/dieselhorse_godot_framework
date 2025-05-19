
import git
import glob
import os
import shutil
import util

util.cwdhack()

def copyglob(sources, destination):
    shutil.rmtree(destination, ignore_errors=True)
    print(destination)
    os.makedirs(destination, exist_ok=True)

    for source in sources:
        print("", source)
        source_files = glob.glob(source)
        for file in source_files:
            print("", "", file)
            shutil.copy(file, destination)

def restore_deleted_uid_files():
    """Restore any .cs.uid files that Git has marked as deleted using GitPython"""

    # Get the current repository
    repo = git.Repo('.')
    
    # Find deleted .cs.uid files
    deleted_files = []
    for item in repo.index.diff(None):
        # Check if this is a deleted file with .cs.uid extension
        if item.change_type == 'D' and item.a_path.endswith('.cs.uid'):
            deleted_files.append(item.a_path)
    
    # Restore the deleted files
    if deleted_files:
        print(f"Restoring {len(deleted_files)} deleted .cs.uid files:")
        for file_path in deleted_files:
            print(f"  Restoring: {file_path}")
            repo.git.checkout('--', file_path)
    else:
        print("No deleted .cs.uid files found.")

def revert_whitespace_only_changes():
    """Revert any files that differ only in whitespace using direct Git commands"""
    # Get the current repository
    repo = git.Repo('.')
    
    # Get list of modified files directly from git status command
    # This should match what command-line git shows
    status_output = repo.git.status('--porcelain')
    
    modified_files = []
    for line in status_output.splitlines():
        # Git status --porcelain format has status codes at the beginning
        # " M filename" indicates modified in working directory but not staged
        # "M  filename" indicates modified and staged
        # "MM filename" indicates modified in both staging and working directory
        if line.startswith(' M') or line.startswith('M ') or line.startswith('MM'):
            # Extract the filename (starts at position 3)
            file_path = line[3:]
            modified_files.append(file_path)
    
    whitespace_only_changes = []
    
    for file_path in modified_files:
        # For each modified file, check if only whitespace changed
        try:
            # Get the content from HEAD (last commit)
            head_content = repo.git.show(f"HEAD:{file_path}")
            
            # Get the content from working directory
            with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                working_content = file.read()
            
            # Normalize content by removing all whitespace
            import re
            
            def normalize_content(content):
                # Remove all whitespace and line endings
                return re.sub(r'\s+', '', content)
            
            head_normalized = normalize_content(head_content)
            working_normalized = normalize_content(working_content)
            
            # If the normalized content is identical, only whitespace has changed
            if head_normalized == working_normalized:
                whitespace_only_changes.append(file_path)
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            continue
    
    # Revert the files with whitespace-only changes
    print(f"Reverting {len(whitespace_only_changes)} files with whitespace-only changes:")
    for file_path in whitespace_only_changes:
        print(f" Reverting: {file_path}")
        repo.git.checkout('--', file_path)

def run():
    copyglob(['../dec/src/*.cs'], 'project/thirdparty/dec')
    copyglob(['../dec/extra/recorder_enumerator/src/*.cs'], 'project/thirdparty/dec/recorder_enumerator')

    copyglob(['../ghi/src/*.cs'], 'project/thirdparty/ghi')

    copyglob(['../arbor/src/*.cs'], 'project/thirdparty/arbor')
    copyglob(['../arbor/arbor-generator/*.cs', '../arbor/arbor-generator/*.csproj'], 'project/thirdparty/arbor/arbor-generator')

    # Restore any .cs.uid files that were deleted
    restore_deleted_uid_files()

    # Revert files with whitespace-only changes
    revert_whitespace_only_changes()

    util.run(["dotnet", "restore"], check=True)

if __name__ == '__main__':
    run()
