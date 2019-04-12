# Simple Web Application -- k8s-webserver

__Version:__ `0.5.2`
__Last Updated:__ 2019-04-11


Simple [Flask](https://flask.io) server to demonstrate K8s capabilities; run with `--help` to see the CLI options available.

# Run locally

This uses ['pipenv'](https://docs.pipenv.org) to build a local virtualenv and run the application, see the docs for how to install it (essentially, `brew install pipenv`) then:

```bash
    pipenv install
    pipenv run ./run_server.py [options]
```

the `install` command is necessary only once, or if you modify the `Pipenv` file to add dependencies.


# Container

This is built as a container:

```bash
    docker login
    docker build -t massenz/simple-flask:$VERSION -f docker/Dockerfile .
    docker push massenz/simple-flask:$VERSION
```

expecting the following `ENV` args:

```
    ENV DEBUG=''
        SERVER_PORT=8080
        SECURE_PORT=8443
        SECRET='chang3Me'
```

These can be re-defined either using `--env` with `docker run` or via the usual Kubernets method to inject `env` arguments in the template.


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

`TODO: this is still based on a Pod; should be refactored to a StatefulSet`

First create the backing DB (based on MongoDB):

    kubectl apply -f config/backend.yaml

This will create a `PersistentVolumeClaim` that will be mounted by the
`mongo` Pod and will retain data across restarts (this is not, however
a `StatefulSet`).

The "fronting" service for this Pod makes it reachable via:

    mongodb://backend:27017


The front-end Web tier (load-balanced via the `frontend` Service) is created via a `Deployment`
composed of `replicas` nodes (currently, 3):

    kubectl apply -f frontend.yaml

Check that the web servers are up and running:

    kubectl get pods

Inside the cluster, several `Env` variables will point to various services; however,
the K8s DNS will resolve the services (using the `Service`'s `name`).

You can deploy the `utils` Pod to have access to a few utilities (`curl`, `nslookup`, etc.) from within the cluster:

```
kubectl apply -f configs/utils.yaml
```

```bash
$ kubectl exec -it utils -- \
        curl -v http://frontend/config | python -m json.tool

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

$ kubectl exec -it utils -- \
        curl -X POST -d '{"_id": "100", "name": "Rebo", "job": "Cisco"}' \
          -H "Content-type: application/json" \
          http://frontend/api/v1/entity

{"msg":"inserted"}

$ kubectl exec -it frontend-cluster-4q8j5 -- curl -fs \
          -H "Content-type: application/json" \
          http://frontend/api/v1/entity/100

[{"_id": "100", "job": "Cisco", "name": "Rebo"}]
```

# Ingress Controller

Deployed in the manner described above, the service is unreachable from outside the Kubernetes cluster; in order to make it reachable, we deploy an [Ingress Controller based on Ngnix](https://kubernetes.io/docs/tasks/access-application-cluster/ingress-minikube/#enable-the-ingress-controller).

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
     paths:
     - path: /kmaps/*
       backend:
         serviceName: kmaps
         servicePort: 80
     - path: /kmaps/v2/*
       backend:
         serviceName: kmaps-v2
         servicePort: 80
```

Deploy the `ingress.yaml` spec:

```bash
kubectl apply -f configs/ingress.yaml
```

and modify `/etc/hosts` so that `frontend.info` points to the `minikube ip`; then the Flask frontend will be reachable at: `http://frontend.info/kmaps/`.

Right now, however, as we haven't deployed yet the `kmaps-v2` service, `http://frontend.info/kmaps/v2/` will yield a `503 Service Unavailable` response (which is different from the `404` one would get by simply using a random URL).

### Deploy the `v2` service



