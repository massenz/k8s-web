# Simple Web Application -- k8s-webserver

![Version](https://img.shields.io/badge/Version-0.5.7-blue)
![Released](https://img.shields.io/badge/Released-2020.09.06-green)

[![Author](https://img.shields.io/badge/Author-M.%20Massenzio-green)](https://bitbucket.org/marco)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
![OS Debian](https://img.shields.io/badge/OS-Linux-green)


A simple two-tier web app, using [Flask](https://flask.io) and [MongoDB](https://mongodb.com) 
to experiment and learn K8s capabilities.


## Container Builde

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
     --env DEBUG='--debug' SERVER_PORT=9900 SECRET='chang3Me'
```

These can be re-defined either using `--env` with `docker run` or via the usual Kubernets method to inject `env` arguments in the template.

## Kubernets Dashboard

To run the [K8s Dashboard](https://kubernetes.io/docs/tasks/access-application-cluster/web-ui-dashboard/) locally, it requires some security configurations; detailed instructions [here](https://github.com/kubernetes/dashboard/blob/master/docs/user/access-control/creating-sample-user.md):

```shell
$ kubectl create ns kubernetes-dashboard
$ kubectl apply -f admin.yaml
$ kubectl apply -f admin-binding.yaml
$ kubectl -n kubernetes-dashboard describe secret \
      $(kubectl -n kubernetes-dashboard get secret | \
        grep admin-user | awk '{print $1}')
```

More details on [Kubernetes Authentication](https://kubernetes.io/docs/reference/access-authn-authz/authentication/).


## ConfigMaps

The `frontend.yaml` configuration contains the definition of a
[ConfigMap](https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap/):

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: frontend-config

data:
  config.yaml: |
    # Used as ConfigMap to run the server in k8s.
    server:
      workdir: /var/lib/flask

    db:
      # Here the 'hostname' must match the Service `name`
      # fronting the backend (see backend-service.yaml)
      uri: "mongodb://backend:27017/my-db"
      collection: "sampledata"
```

which is then used to configure the Web server, by first defining a `Volume`:

```yaml
      volumes:
      - name: config
        configMap:
          name: frontend-config
```

and then mounting it on the container:

```yaml
  spec:
    containers:
    - image: massenz/simple-flask:0.5.1
      ...
      volumeMounts:
      - name: config
        mountPath: "/etc/flask"
        readOnly: true
```

which creates a file in the container at `/etc/flask/config.yaml`.

If the previous `ConfigMap` spec were to be saved to a `config.yaml` file, it could have been
created using:

    kubectl create configmap frontend-config --from-file=config.yaml


# 2-tier Service in Kubernetes

## Backing DB (MongoDB 3.7.9)

First create the backing DB cluster (a MongoDB ReplicaSet, :

    kubectl apply -f config/backend.yaml

This will create a 3-node replicated cluster `StatefulSet`, and the respective
`PersistentVolumeClaim`s that will be mounted by the `mongo-node-x` Pods and will retain data
across restarts:


In order to initialize the Mongo Replicaset (**not** a Kubernetes `ReplicaSet`) one needs to run
 the initializaion script:

    kubectl exec -i mongo-node-0 -- mongo mongo-node-0.mongo-cluster/local < mongo/mongo-replicas.js

The cluster is reachable at the following URI:

    mongodb://mongo-node-0.mongo-cluster,mongo-node-1.mongo-cluster,mongo-node-2.mongo-cluster:27017

(see also the `ConfigMap` defined in `frontend.yaml`).


## Frontend (Web) Service (Python Flask server)

The front-end Web tier (load-balanced via the `frontend` Service) is created via a `Deployment`
composed of `replicas` nodes (currently, 3):

    kubectl apply -f frontend.yaml

Check that the web servers are up and running:

    kubectl get pods

Inside the cluster, several `Env` variables will point to various services; however,
the K8s DNS will resolve the services (using the `Service`'s `name`).

The service is exposed on port `31000` of the Node's IP address:

    minikube service list
    
will show exactly the URL to hit to reach the service:

    |-------------|---------------|--------------|----------------------------|
    |  NAMESPACE  |     NAME      | TARGET PORT  |            URL             |
    |-------------|---------------|--------------|----------------------------|
    | default     | frontend      | http/80      | http://192.168.5.130:31000 |


## Utility pod (`massenz/dnsutils`)

You can deploy the `utils` Pod to have access to a few utilities (
`curl`, `nslookup`, etc.) from within the cluster:

```
kubectl apply -f configs/utils.yaml
```

In particular, [`httpie`](https://httpie.org/docs) is quite useful to probe around the API:

```bash
$ kubectl exec -it utils -- http frontend/config

{
    "application_root": "/",
    "db_collection": "sampledata",
    "db_uri": "mongodb://backend:27017/my-db",
    "debug": false,
    "env": "production",
    "explain_template_loading": false,
    "health": "UP",
    ...
}

$ kubectl exec -it utils -- http frontend/api/v1/entity name=Marco job=Architect company=Adobe

HTTP/1.0 201 CREATED
Content-Length: 19
Content-Type: application/json
Date: Mon, 07 Sep 2020 07:26:30 GMT
Location: http://frontend/api/v1/entity/5f55e0a6baa67e0325d2cd9d
Server: Werkzeug/1.0.1 Python/3.7.9

{
    "msg": "inserted"
}

$ kubectl exec -it utils -- http frontend/api/v1/entity/5f55e0a6baa67e0325d2cd9d
HTTP/1.0 200 OK
Content-Length: 85
Content-Type: application/json
Date: Mon, 07 Sep 2020 07:27:16 GMT
Server: Werkzeug/1.0.1 Python/3.7.9

{
    "company": "Adobe",
    "id": "5f55e0a6baa67e0325d2cd9d",
    "job": "Architect",
    "name": "Marco"
}
```

# Ingress Controller

    TODO(marco): This is currently NOT working.

Deployed in the manner described above, the service is unreachable from outside the Kubernetes cluster; in order to make it reachable, we deploy an [NGNIX Ingress Controller](https://kubernetes.github.io/ingress-nginx/).

**NOTE**
> The following is based on the [Kubernetes tutorial on Ingress Controller](https://kubernetes.io/docs/tasks/access-application-cluster/ingress-minikube/#enable-the-ingress-controller).

The first step is to actually deploy the Controller:

```bash
minikube addons enable ingress

kubectl get pods -n kube-system

  ...
  nginx-ingress-controller-5984b97644-rnkrg   1/1       Running ...

kubectl expose deployment frontend-cluster --port 80 --target-port 8080 \
    --type NodePort --name kmaps
```

A new `NodePort` service is now available:

```bash
kubectl get service kmaps

kmaps
NAME    TYPE       CLUSTER-IP      EXTERNAL-IP   PORT(S)        AGE
kmaps   NodePort   10.105.74.231   <none>        80:31787/TCP   81s
```

this is reachable from inside the cluster as the `kmaps` service on port 80:

```bash
kubectl exec -ti utils -- curl -fs http://kmaps

  <!DOCTYPE html>
  <html xmlns="http://www.w3.org/1999/html">
  <head
    ...
  </html>
```

(which is not particularly useful) but, more interestingly from outside the cluster too:

```bash
minikube service kmaps
```

will open a browser window on the main app page, reachable at `http://192.168.8.130:31787` (use `minikube service list` to find the IP/Port for the service).

## NGNIX Web configuration

The real point of adding an Ingress controller is however to somehow add behavior to the incoming requests; in the example in `configs/ingress.yaml` this is to add multiple "virtual hosts" to this cluster:

```yaml
apiVersion: extensions/v1beta1
kind: Ingress
...
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /$1
...
      paths:
      - path: /kmaps/?(.*)
        backend:
          serviceName: kmaps
          servicePort: 80
      - path: /kmaps/v2/?(.*)
        backend:
          serviceName: kmaps-v2
          servicePort: 80
```

**NOTE**
> The `rewrite` annotation is described [here](https://kubernetes.github.io/ingress-nginx/examples/rewrite/) and is required, so that application URLs can be mapped back to what the Web application expects.

Deploy the `ingress.yaml` spec:

```bash
kubectl apply -f configs/ingress.yaml
```

and (optionally) modify `/etc/hosts` so that `frontend.info` points to the `minikube ip`; then the Flask frontend will be reachable at: `http://frontend.info/kmaps/`.

**NOTE**
> This is only to emulate a DNS service that would map the cluster/service domain - it is entirely irrelevant for the purposes of the example here.
