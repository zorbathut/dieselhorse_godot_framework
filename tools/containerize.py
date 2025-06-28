
import argparse
import build_utils
import os
import util

util.cwdhack()

# Set up environment variables
BUILD_NUMBER = os.getenv('BUILD_NUMBER', 'manual')
GBCMSB_ID = f"gbcmsb-{BUILD_NUMBER}"


DOCKER_UID = ["--user", f"{os.getuid()}:{os.getgid()}"]

VOLUMESPEC = ["-v", f"{os.getcwd()}:{os.getcwd()}"]
# sure am glad that works in all cases!
# just close your eyes for a second okay
if "VOLUMES_FROM" in os.environ:
    VOLUMESPEC = ["--volumes-from", os.environ["VOLUMES_FROM"]]
# whew! don't worry, I didn't write any code, this is all fine

def build_image(target):
    """Build Docker Image."""
    docker_image = "quay.io/podman/stable:v5.0.2-immutable"
    storage_path = "/var/lib/jenkins/podman-storage"

    image_tar = f"godot-{target}-{GBCMSB_ID}.tar"

    # Remove the image tar files if they exist, but it's OK if they don't
    if os.path.exists(f"build/godot-build-containers/{image_tar}"):
        os.unlink(f"build/godot-build-containers/{image_tar}")

    # Commands to run inside the Docker container
    msb_command = f'./msb.sh {GBCMSB_ID} {target}'
    save_image = f"podman save localhost/godot-{target}:{GBCMSB_ID} -o {image_tar}"

    docker_run_command = [
        "docker", "run", "--rm", "--privileged"] + DOCKER_UID + VOLUMESPEC + [
            "-v", f"{storage_path}:/var/lib/containers/storage",
            "-w", f"{os.getcwd()}/build/godot-build-containers",
            docker_image, "/bin/bash", "-c",
        f"{msb_command} && {save_image}"
    ]

    util.run(docker_run_command, check = True)

    # Import the image into the Docker environment of the host
    util.run(["docker", "load", "-i", f"build/godot-build-containers/{image_tar}"])

    return f"localhost/godot-{target}:{GBCMSB_ID}"

def run(container_type, command, arguments):
    # build container
    image_name = build_image(container_type)

    # then run the script
    util.run(["docker", "run", "--rm"] + DOCKER_UID + VOLUMESPEC + [
        "-w", f"{os.getcwd()}",
        image_name, "./tool.bat", command] + arguments, check = True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = "Containerize")
    build_utils.decorate_argparse_with_dev(parser)

    # Add positional arguments
    parser.add_argument('container_type', help='Type of container')
    parser.add_argument('command', help='Command to run')
    parser.add_argument('arguments', nargs='*', help='Additional arguments')

    args = parser.parse_args()
    run(args.container_type, args.command, args.arguments)
