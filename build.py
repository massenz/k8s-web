#!/usr/bin/env python3
#
# Copyright (c) 2020 AlertAvert.com  All rights reserved.
# Created by M. Massenzio, 2020-11-24

# Builds the container and pushes to Docker Hub
import os
import sys
from pathlib import Path

from halo import Halo
from sh import docker, ErrorReturnCode
from app.utils import version


basedir = Path(__file__).parent.absolute()
os.chdir(f"{basedir!s}")
print(f"Building server container from: {basedir!s}")


try:
    for name in ("simple-flask", "mongo-replicas", "opaserver"):
        image = f"massenz/{name}:{version()}"
        dockerfile = Path("docker") / f"Dockerfile.{name}"

        with Halo(text=f"Building container {image}", spinner='dots'):
            res = docker.build("-t", image, "-f", f"{dockerfile}", ".")
        print(f"[SUCCESS] Image {image} built")

        if len(sys.argv) > 1 and sys.argv[1] == "--push":
            with Halo(text=f"Pushing container {image}", spinner='dots'):
                res = docker.push(f"{image}")
            print(f"[SUCCESS] Image {image} pushed to DockerHub")

except ErrorReturnCode as err:
    print(err.stdout)
    print(f"{err.stderr}", file=sys.stderr)
    print(f"[ERROR] {err}", file=sys.stderr)
