import os.path
import subprocess
import sys
import re
from enum import Enum
from collections import defaultdict


class StagedFileStatus(Enum):
    ADDED = "added"
    RENAMED = "renamed"
    DELETED = "deleted"
    MODIFIED = "modified"
    CONFLICT = "conflict"  # this can be ignore in the context of the hook but i would rather keep it for completion's sake


TARGET_DIRECTORIES = {"project"}


def get_staged_files():
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"], capture_output=True, text=True
    )
    return result.stdout.strip().split("\n") if result.stdout else []


def get_tracked_files():
    result = subprocess.run(
        ["git", "ls-files"],
        check=True,
        stdout=subprocess.PIPE,
        text=True
    )
    return set(result.stdout.strip().splitlines())


def get_staged_files_by_status():
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-status"], capture_output=True, text=True
    )

    files_by_status = defaultdict(set)

    if result.stdout:
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            status, filename = line.split("\t", 1)
            if status == "M":
                files_by_status[filename] = StagedFileStatus.MODIFIED
            elif status == "R":
                files_by_status[filename] = StagedFileStatus.RENAMED
            elif status == "C":
                files_by_status[filename] = StagedFileStatus.CONFLICT
            elif status == "A":
                files_by_status[filename] = StagedFileStatus.ADDED
            elif status == "D":
                files_by_status[filename] = StagedFileStatus.DELETED

    return dict(files_by_status)


def is_valid_file(file_path, file_extension, allow_deleted=False):
    # ignore anything that does not have a related extension
    if not file_path.endswith(file_extension):
        return False

    # ignore deleted files
    if not os.path.isfile(file_path) and not allow_deleted:
        return False

    # work with all staged files that are part of that directory or its children subdirectories
    if TARGET_DIRECTORIES and not any(
            file_path.startswith(dir_name + "/") for dir_name in TARGET_DIRECTORIES
    ):
        return False

    return True


def is_using_namespace(filepath, namespace):
    regexInput = r"^\s*using\s+{}\b[.;]".format(re.escape(namespace))

    pattern = re.compile(regexInput, re.IGNORECASE)

    with open(filepath, "r", encoding="utf-8", errors="ignore") as file:
        for line_number, line in enumerate(file, start=1):
            if pattern.search(line):
                print(
                    f"Error found in {filepath} at line {line_number}: {line.strip()}"
                )
                return True

    return False


def are_any_cs_files_using_forbidden_using_declarations():
    staged_files = get_staged_files()
    filtered_files = [file for file in staged_files if is_valid_file(file, ".cs")]
    fordidden_namespaces = ["Comp", "Prop"]

    if not filtered_files:
        print("No relevant staged files found")
        return False

    error_found = False
    for file in filtered_files:
        for namespace in fordidden_namespaces:
            if is_using_namespace(file, namespace):
                error_found = True

    return error_found


def are_any_cs_uid_missing_or_remaining():
    staged_files = get_staged_files_by_status()
    tracked_files = get_tracked_files()

    all_staged_cs_files = {
        file: status
        for file, status in staged_files.items()
        if is_valid_file(file, ".cs", True)
    }

    all_staged_cs_uid_files = {
        file: status
        for file, status in staged_files.items()
        if is_valid_file(file, ".cs.uid", True)
    }

    not_deleted_cs_files = {
        file: status
        for file, status in all_staged_cs_files.items()
        if status not in { StagedFileStatus.DELETED }
    }

    not_deleted_cs_uid_files = {
        file: status
        for file, status in all_staged_cs_uid_files.items()
        if status not in { StagedFileStatus.DELETED }
    }

    # check if they are any orphaned .cs files
    # for any file that is not deleted, 
    # the corresponding cs.uid should be either staged or already tracked 
    for file, _ in not_deleted_cs_files.items():
        file_to_check = file + ".uid"
        file_not_staged = file_to_check not in not_deleted_cs_uid_files;
        file_not_tracked = file_to_check not in tracked_files
        if file_not_staged and file_not_tracked:
            print("**********\n")
            print(
                f"UID mismatch for existing file!\n{file} : EXISTS \n{file_to_check} : NOT FOUND"
            )
            print(
                f"Please run the project in editor mode to generate {file_to_check}. Then, stage it before commiting"
            )
            print("**********\n")
            return True

    # chek if there are any orphaned cs.uid files
    # for any file that is not deleted,
    # the corresponding cs.uid should be either staged or already tracked 
    for file, _ in not_deleted_cs_uid_files.items():
        file_to_check = file[:-4] # remove the .uid extension 
        file_not_staged = file_to_check not in not_deleted_cs_files;
        file_not_tracked = file_to_check not in tracked_files
        if file_not_staged and file_not_tracked:
            print("**********\n")
            print(
                f"UID mismatch for existing file!\n{file} : EXISTS \n{file_to_check} : NOT FOUND"
            )
            print(
                f"Either add \"{file_to_check}\" to the project or delete {file}. Then, try again."
            )
            print("**********\n")
            return True

    deleted_cs_files = {
        file: status
        for file, status in all_staged_cs_files.items()
        if status in {StagedFileStatus.DELETED}
    }

    deleted_cs_uid_files = {
        file: status
        for file, status in all_staged_cs_uid_files.items()
        if status in {StagedFileStatus.DELETED}
    }

    # check for orphaned deletions for .cs files
    # the cs.uid should be already staged for deletion, or the file is not there in the first place
    for file, _ in deleted_cs_files.items():
        file_to_check = file + ".uid"
        file_not_staged_for_deletion = file_to_check not in deleted_cs_uid_files
        file_tracked = file_to_check in tracked_files

        if file_not_staged_for_deletion and file_tracked:
            print("**********\n")
            print(
                f"UID mismatch for deleted file!\n{file} : DELETED \n{file_to_check} : NOT DELETED"
            )
            print(
                f"Delete  \"{file_to_check}\" and try again. If it is already deleted, stage the change and try again"
            )
            print("**********\n")
            return True

    # check for orphaned deletions for .cs.uid files
    # the cs.uid should be already staged for deletion, or the file is not there in the first place
    for file, _ in deleted_cs_uid_files.items():
        file_to_check = file[:-4]
        file_not_staged_for_deletion = file_to_check not in deleted_cs_files
        file_tracked = file_to_check in tracked_files

        if file_not_staged_for_deletion and file_tracked:
            print("**********\n")
            print(
                f"UID mismatch for deleted file!\n{file} : DELETED \n{file_to_check} : NOT DELETED"
            )
            print(
                f"Delete  \"{file_to_check}\" and try again. If it is already deleted, stage the change and try again"
            )
            print("**********\n")
            return True


    return False


def main():
    if are_any_cs_files_using_forbidden_using_declarations():
        print("\nCommit aborted: Forbidden using declaration.\n")
        sys.exit(-1)

    if are_any_cs_uid_missing_or_remaining():
        print(
            "\nCommit aborted: UID mismatch!\n"
        )
        sys.exit(-1)

    sys.exit(0)


if __name__ == "__main__":
    main()
