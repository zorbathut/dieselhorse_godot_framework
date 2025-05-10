#!/usr/bin/env bash
set -eux

basedir=$(cd $(dirname "$0"); pwd)

source $basedir/setup.sh

img_version=$1
files_root="$basedir/files"

mkdir -p logs

"$podman" build -t godot-fedora:${img_version} -f Dockerfile.base . 2>&1 | tee logs/base.log

podman_build() {
    # Enable pipefail to capture the exit status of podman build
    set -o pipefail

  # You can add --no-cache as an option to podman_build below to rebuild all containers from scratch.
  "$podman" build \
    --build-arg img_version=${img_version} \
    -v "${files_root}":/root/files:z \
    -t godot-"$1:${img_version}" \
    -f Dockerfile."$1" . \
    2>&1 | tee logs/"$1".log

    # Capture the exit status
    local status=$?

    # Disable pipefail
    set +o pipefail

    # Return the captured status
    return $status
}

podman_build $2
