
import argparse
import build_utils
import multiprocessing
import os
import psutil
import shutil
import util
import subprocess
import filecmp

util.cwdhack()

def copy_git_hooks():
    git_root = "."  # this used to be determined at runtime but relied on the git executable
    
    hook_folder_source_path = os.path.normpath(os.path.join(git_root, "tools", "git_hooks"))
    
    hook_folder_destination_path = os.path.normpath(os.path.join(git_root, ".git", "hooks"))
    
    print("Installing git hooks")
    for item in os.listdir(hook_folder_source_path):
        src_path = os.path.join(hook_folder_source_path, item)
        dest_path = os.path.join(hook_folder_destination_path, item)
                
        if os.path.isfile(src_path):  # Only process files
            # copy anything not existing or different
            if not os.path.exists(dest_path) or not filecmp.cmp(src_path, dest_path, shallow=False):
                print(f"Copying: {os.path.relpath(src_path, git_root)} -> {os.path.relpath(dest_path, git_root)}")
                shutil.copy2(src_path, dest_path)  # Copy with metadata   
    
    print("Git hook installation complete")

def run(dev):
    
    copy_git_hooks()
    
    # kick priority down to make builds smoother
    # can't do this on linux unfortunately; shell out to a niced build_editor?
    if util.platformswitch(linux = False, windows = True, mac = False):
        proc = psutil.Process(os.getpid())
        proc.nice(psutil.IDLE_PRIORITY_CLASS)

    platform = util.platformswitch(linux = "linuxbsd", windows = "windows", mac = "osx")

    cores = multiprocessing.cpu_count()
    print(f"Running with {cores} cores")
    
    # Clear out old generated binaries
    shutil.rmtree("godot/bin", ignore_errors=True)

    # Build the executable binary
    util.run([
            "scons",
            "-j", f"{cores}",
            f"p={platform}",
            "target=editor"] +
            (["dev_build=yes"] if dev else []) +
            build_utils.get_build_opts() +
            [f"precision={build_utils.get_float_precision()}",
            "extra_suffix=dev" if dev else "extra_suffix=release",
            "output_suffix=.universal.editor.exe",
        ], check=True, cwd="godot", env=build_utils.get_env())
    
    # Build the lib binary
    util.run([
            "scons",
            "-j", f"{cores}",
            f"p={platform}",
            "target=editor"] +
            (["dev_build=yes"] if dev else []) +
            build_utils.get_build_opts() +
            [f"precision={build_utils.get_float_precision()}",
            "library_type=shared_library",
            "extra_suffix=lib_dev" if dev else "extra_suffix=lib_release",
            "output_suffix=.universal.editor.dll",
        ], check=True, cwd="godot", env=build_utils.get_env())
    
    # Generate Mono glue files.
    util.run([
            os.path.join("bin", "godot.universal.editor.exe"),
            "--headless",
            "--generate-mono-glue", "./modules/mono/glue",
        ], check=True, cwd="godot", env=build_utils.get_env())

    # Make necessary directory
    os.makedirs("godot/bin/GodotSharp/Tools/nupkgs", exist_ok=True)
    
    # Build NuGet packages.
    util.run([
           "python",
           "./modules/mono/build_scripts/build_assemblies.py",
           "--godot-output-dir", "./bin"] +
           build_utils.get_build_assemblies_opts() +
           [f"--precision={build_utils.get_float_precision()}",
        ], check=True, cwd="godot", env=build_utils.get_env())
    
    # Restore the .net code
    util.run([
            "dotnet",
            "restore",
        ], check=True, cwd="project", env=build_utils.get_env())

    # import with headless
    util.run([
            os.path.join("..", "godot", "bin", "godot.universal.editor.exe"),
            "--headless",
            "--import",
        ], check=True, cwd="project", env=build_utils.get_env())
        
    print("If it just printed a bunch of errors about \"Freeing unknown RID\", you can ignore those.")
    print("If it didn't, let Zorba know so he can remove this message.")

    # Ramp priority back up for the editor itself.
    if util.platformswitch(linux = False, windows = True, mac = False):
        proc.nice(psutil.NORMAL_PRIORITY_CLASS)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Build editor")
    build_utils.decorate_argparse_with_dev(parser)
    args = parser.parse_args()

    # on linux and mac, we *can* forcibly renice the entire process down, we just can't return to normal
    # that's OK if we're being called directly!
    # annoyingly this still isn't as smooth as it is on Windows
    if util.platformswitch(linux = True, windows = False, mac = True):
        os.nice(19)

    run(args.dev)
