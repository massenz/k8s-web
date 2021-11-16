# Simple Web Application -- k8s-webserver

![Version](https://img.shields.io/badge/Version-0.6.1-blue)
![Released](https://img.shields.io/badge/Released-2020.11.27-green)

[![Author](https://img.shields.io/badge/Author-M.%20Massenzio-green)](https://bitbucket.org/marco)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
![OS Debian](https://img.shields.io/badge/OS-Linux-green)


A simple two-tier web app, using [Flask](https://flask.io) and [MongoDB](https://mongodb.com)
to experiment and learn [Kubernetes](https://kubernetes.io) capabilities.

## GitOps Model

This is only the "development" part of the services, which contains solely the code for the application,
and whose generated artifact(s) are the Docker containers.

The associated ["deployment"](https://bitbucket.org/marco/k8s-web-config) project contains all the necessary automation to deploy the service on a Kubernetes cluster.

## Container Build

Build the container (the value of `$VERSION` will be derived from `build.settings`):

```shell
$ ./build.py

[SUCCESS] Image massenz/simple-flask:$VERSION built
```
then run it (get the current version from `build.settings`):

```
$ docker run --rm -d mongo:3.7
$ docker run --rm -d -p 8088:8080 massenz/simple-flask:$VERSION
```

the server is then reachable at [http://localhost:8080].

You can change some of the server arguments using the following `--env` args:

```
$ docker run --rm -d -p 8088:8080 massenz/simple-flask:$VERSION \
     --env DEBUG='--debug' --env SERVER_PORT=9900 --env SECRET='chang3Me'
```

Before deploying the application to Kubernetes, push the built containers to [Docker Hub](http://hub.docker.com):

```
$ ./build.py --push
```

# Service API

`TODO: Describe the API here`

The main service page (`index.html`) will show a brief summary of the available endpoints: reach the service from a browser at `http://localhost:8080`.
