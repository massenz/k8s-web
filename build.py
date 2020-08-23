#!/usr/bin/env python3

# Builds the container and pushes to Docker Hub
import sys
from pathlib import Path

from halo import Halo
from sh import docker, ErrorReturnCode
from utils import version

IMAGE = "massenz/simple-flask"
DOCKERFILE = Path("docker")/"Dockerfile"

image = f"{IMAGE}:{version()}"

try:
    with Halo(text=f"Building container {image}", spinner='dots'):
        res = docker.build("-t", image, "-f", f"{DOCKERFILE}", ".")
    print(f"[SUCCESS] Image {image} built")

    with Halo(text=f"Pushing container {image}", spinner='dots'):
        res = docker.push(f"{image}")
    print(f"[SUCCESS] Image {image} pushed to DockerHub")

except ErrorReturnCode as err:
    print(err.stdout)
    print(f"{err.stderr}", file=sys.stderr)
    print(f"[ERROR] {err}", file=sys.stderr)
