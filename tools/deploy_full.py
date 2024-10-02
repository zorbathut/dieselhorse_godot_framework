
import build_utils
import os
import shutil
import util

util.cwdhack()

# Set up environment variables
BUILD_NUMBER = os.getenv('BUILD_NUMBER', 'manual')
GBCMSB_ID = f"gbcmsb-{BUILD_NUMBER}"

LINUX_IMAGE_TAR = f"godot-linux-{GBCMSB_ID}.tar"
WINDOWS_IMAGE_TAR = f"godot-windows-{GBCMSB_ID}.tar"

DOCKER_UID = ["--user", f"{os.getuid()}:{os.getgid()}"]

VOLUMESPEC = ["-v", f"{os.getcwd()}:{os.getcwd()}"]
# sure am glad that works in all cases!
# just close your eyes for a second okay
if "VOLUMES_FROM" in os.environ:
    VOLUMESPEC = ["--volumes-from", os.environ["VOLUMES_FROM"]]
# whew! don't worry, I didn't write any code, this is all fine

def build_docker_image():
    """Build Docker Image."""
    docker_image = "quay.io/podman/stable:v5.0.2-immutable"
    storage_path = "/var/lib/jenkins/podman-storage"

    # Remove the image tar files if they exist, but it's OK if they don't
    if os.path.exists(f"build/godot-build-containers/{LINUX_IMAGE_TAR}"):
        os.unlink(f"build/godot-build-containers/{LINUX_IMAGE_TAR}")
    if os.path.exists(f"build/godot-build-containers/{WINDOWS_IMAGE_TAR}"):
        os.unlink(f"build/godot-build-containers/{WINDOWS_IMAGE_TAR}")

    # Commands to run inside the Docker container
    msb_command = f'./msb.sh {GBCMSB_ID}'
    save_linux_image = f"podman save localhost/godot-linux:{GBCMSB_ID} -o {LINUX_IMAGE_TAR}"
    save_windows_image = f"podman save localhost/godot-windows:{GBCMSB_ID} -o {WINDOWS_IMAGE_TAR}"
    
    docker_run_command = [
        "docker", "run", "--rm", "--privileged"] + DOCKER_UID + VOLUMESPEC + [
            "-v", f"{storage_path}:/var/lib/containers/storage",
            "-w", f"{os.getcwd()}/build/godot-build-containers",
            docker_image, "/bin/bash", "-c",
        f"{msb_command} && {save_linux_image} && {save_windows_image}"
    ]
    
    util.run(docker_run_command, check = True)

    # Import the image into the Docker environment of the host
    util.run(["docker", "load", "-i", f"build/godot-build-containers/{LINUX_IMAGE_TAR}"])
    util.run(["docker", "load", "-i", f"build/godot-build-containers/{WINDOWS_IMAGE_TAR}"])

def build_deploy(target):
    """Build and deploy for a specific target."""
    image_name = f"localhost/godot-{target}:{GBCMSB_ID}"
    util.run(["docker", "run", "--rm"] + DOCKER_UID + VOLUMESPEC + [
        "-w", f"{os.getcwd()}",
        image_name, "./tool.bat", "deploy", f"--target={target}"], check = True)

def create_artifacts():
    """Create artifacts by zipping directories."""
    projectname = build_utils.get_project_name()
    
    # Get a list of directories to zip
    dirs_to_zip = [d for d in os.listdir("deploy") if os.path.isdir(os.path.join("deploy", d))]
    
    # Prepare commands for Docker
    commands = []
    for dir_name in dirs_to_zip:
        commands.extend([
            f"(cd deploy && zip -9 -r {dir_name}.zip {dir_name})",
        ])
    
    # Run Docker command to create zip files
    util.run([
        "docker", "run"] + DOCKER_UID + VOLUMESPEC + ["--rm", "-w", f"{os.getcwd()}",
        f"localhost/godot-linux:{GBCMSB_ID}", "/bin/bash", "-c",
        " && ".join(commands)
    ], check=True)
    
    # Prepare artifact directory
    shutil.rmtree("artifact", ignore_errors=True)
    os.makedirs("artifact", exist_ok=True)
    
    # Move zip files to artifact directory
    for zip_file in os.listdir("deploy"):
        if zip_file.endswith(".zip"):
            shutil.move(os.path.join("deploy", zip_file), os.path.join("artifact", zip_file))

def clean_up():
    """Clean up Docker containers and images."""
    if False:
        # disabled because it wasn't working and is less important now
        util.run(
            ["docker", "ps", "-a", "-q", "--filter", f"ancestor=localhost/godot-linux:{GBCMSB_ID}", "|",
            "xargs", "-r", "docker", "rm", "-f"], shell = True, check = True)
        util.run(
            ["docker", "ps", "-a", "-q", "--filter", f"ancestor=localhost/godot-windows:{GBCMSB_ID}", "|",
            "xargs", "-r", "docker", "rm", "-f"], shell = True, check = True)

        # Remove the image tar files
        os.remove(LINUX_IMAGE_TAR)
        os.remove(WINDOWS_IMAGE_TAR)

def run():
    try:
        # wipe deploy directory entirely
        shutil.rmtree("deploy", ignore_errors = True)

        # Build Docker Image
        build_docker_image()

        # Build and deploy for Linux
        build_deploy('linux')

        # Build and deploy for Windows
        build_deploy('windows')

        # Create artifacts
        create_artifacts()
    finally:
        # Always clean up
        clean_up()

if __name__ == '__main__':
    run()
