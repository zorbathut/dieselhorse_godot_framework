
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

parser = argparse.ArgumentParser()
parser.add_argument("--target", required = True, choices=["linux", "windows"])
args = parser.parse_args()

def generate_license_file(output_file, separator="-"*80):
    output_content = []

    # Step 1: Recursively find and concatenate LICENSE* files in project directory
    for root, dirs, files in os.walk("project"):
        # Skip ONLY the direct project/thirdparty directory
        if root.startswith(os.path.join("project", "thirdparty")):
            continue

        for file in files:
            if file.startswith("LICENSE"):
                license_file = os.path.join(root, file)
                with open(license_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                output_content.append(content)
                output_content.append("\n\n")

    output_content.append(f"\n\n{separator}\n\n")

    # Step 2: Recursively find and concatenate LICENSE* files in project/thirdparty
    thirdparty_path = os.path.join("project", "thirdparty")
    if os.path.exists(thirdparty_path):
        output_content.append("# Third-party Licenses\n\n")
        for subdir in sorted(os.listdir(thirdparty_path)):
            subdir_path = os.path.join(thirdparty_path, subdir)
            if os.path.isdir(subdir_path):
                license_files = []
                for root, dirs, files in os.walk(subdir_path):
                    for file in files:
                        if file.startswith("LICENSE"):
                            license_files.append(os.path.join(root, file))

                if license_files:
                    # Add header with the project name
                    output_content.append(f"## {subdir}\n\n")

                    # Concatenate all license files for this project
                    project_content = []
                    for license_file in license_files:
                        with open(license_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        project_content.append(content)

                    # Add the concatenated content for this project
                    output_content.append("\n\n".join(project_content))
                    # Add a separator after the project
                    output_content.append(f"\n\n{separator}\n\n")

    # Step 3: Append godot/COPYRIGHT.txt
    godot_copyright_path = os.path.join("godot", "COPYRIGHT.txt")
    if os.path.exists(godot_copyright_path):
        output_content.append("# Godot Engine Copyright\n\n")
        with open(godot_copyright_path, 'r', encoding='utf-8') as f:
            content = f.read()
        output_content.append(content)
    
    # Step 4: Accumulate C# license information
    from deploy_licenses import run_license_analysis
    output_content.append(run_license_analysis()["output_text"])

    # Write the combined license file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("".join(output_content))

def run():
    # we do this both to build the mono glue files and to build the editor that we can use to run the deploy code
    # it's possible we should build this separately in our jenkins build, then copy it over
    build_editor.run(False)

    cores = multiprocessing.cpu_count()
    print(f"Running with {cores} cores")

    # Build the binary itself (yay this is no longer two-pass)
    util.run([
            "scons",
            "-j", f"{cores}",
            f"p={args.target}",
            "target=template_release",
            "arch=x86_64",
            "production=yes"] +
            build_utils.get_build_opts() +
            [f"precision={build_utils.get_float_precision()}", 
            # no extra suffix because it conflicts with the export process
        ], check=True, cwd="godot", env=build_utils.get_env())

    # Mono glue files already exist from us building the editor
    # Don't need to build them a second time
    # (but do need to build the editor)
    
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

    # Clear and remake necessary directory
    deploydir = f"deploy/{build_utils.get_project_name()}-{args.target}-{build_utils.get_project_version()}"
    if os.path.exists(deploydir):
        shutil.rmtree(deploydir)
    os.makedirs(deploydir, exist_ok=True)

    # Shove a version file in our .pck
    with open(f"project/buildinfo.xml", "w") as f:
        f.write(f"<BuildInfo><version>{build_utils.get_project_version()}</version><environment>release</environment></BuildInfo>")

    # Run headless export
    util.run([
            "godot/bin/godot.universal.editor.exe",
            "--headless",
            "--path", "project",
            "--export-release", args.target,
            f"../{deploydir}/{build_utils.get_project_name()}",
        ], check=True, env=build_utils.get_env())
        
    # Wipe the version file
    os.remove("project/buildinfo.xml")

    # Copy dec directory over
    shutil.copytree("project/dec", f"{deploydir}/dec")
    
    # Remove everything in COPYRIGHT_INFRINGEMENT directories
    for root, dirs, files in os.walk(deploydir):
        for name in dirs:
            if name == "COPYRIGHT_INFRINGEMENT":
                shutil.rmtree(os.path.join(root, name))
    
    # Verify that a directory starting with `data` exists, because otherwise we've run into that weird bug again where it stops including the data
    if not any(os.path.isdir(os.path.join(deploydir, d)) and d.startswith("data") for d in os.listdir(deploydir)):
        raise RuntimeError(f"Failed to find data directory in {deploydir}")

    # Assemble our final license text
    generate_license_file(os.path.join(deploydir, "LICENSE"))

    if args.target == "linux":
        # All the debug info is shoved in the executable, so let's pull that out
        util.run([
                "strip",
                f"{deploydir}/{build_utils.get_project_name()}",
            ], check=True)
    elif args.target == "windows":
        # Needs an .exe suffix
        os.rename(f"{deploydir}/{build_utils.get_project_name()}", f"{deploydir}/{build_utils.get_project_name()}.exe")
        
    # Generate artifact
    os.makedirs("artifact", exist_ok=True)
    util.run([
        "zip",
        "-9",
        "-r",
        f"{deploydir}.zip",
        f"{deploydir}",
    ], check=True)

if __name__ == '__main__':
    run()
