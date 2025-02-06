import os.path
import subprocess
import sys
import re

TARGET_DIRECTORIES = {"project"}

def get_staged_files():
    result = subprocess.run(["git", "diff", "--cached", "--name-only"], capture_output=True, text=True)
    return result.stdout.strip().split("\n") if result.stdout else []


def is_valid_file(file_path):
    # ignore deleted files
    if not os.path.isfile(file_path):
        return False
    
    # ignore anything that is not a .cs file
    if not file_path.endswith(".cs"): 
        return False
    
    # work with all staged files that are part of that directory or its children subdirectories
    if TARGET_DIRECTORIES and not any(file_path.startswith(dir_name + "/") for dir_name in TARGET_DIRECTORIES): 
        return False
    return True


def is_using_namespace(filepath, namespace):
    regexInput = r"^\s*using\s+{}\b[.;]".format(re.escape(namespace))

    pattern = re.compile(regexInput, re.IGNORECASE)

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as file:
        for line_number, line in enumerate(file, start=1):
            if pattern.search(line):
                print(f"Error found in {filepath} at line {line_number}: {line.strip()}")
                return True

    return False


def main():
    staged_files = get_staged_files()
    filtered_files = [file for file in staged_files if is_valid_file(file)];
    fordidden_namespaces = ["Comp", "Prop"]

    if (not filtered_files):
        print("No relevant staged files found")
        sys.exit(0)

    error_found = False
    for file in filtered_files:
        for namespace in fordidden_namespaces:
            if is_using_namespace(file, namespace):
                error_found = True

    if error_found:
        print("\n Commit aborted: Forbidden using declaration.\n")
        sys.exit(-1)

    print("No forbidden using declaration was found. Proceeding with commit.")
    sys.exit(0)


if __name__ == "__main__":
    main()
