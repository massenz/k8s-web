# Simple Web Application -- k8s-webserver

__Version:__ `0.6.6`
__Last Updated:__ 2019-04-12


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

**NOTE**
> `VERSION` may be different but **must** match the value in `frontend.yaml`

```bash
VERSION=0.5.1 && IMAGE="massenz/simple-flask" && \
    docker build -t $IMAGE:$VERSION -f docker/Dockerfile . && \
    docker push $IMAGE:$VERSION
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


### Deploy the `v2` service

Right now, however, as we haven't deployed yet the `kmaps-v2` service, `http://frontend.info/kmaps/v2/` will yield a `503 Service Unavailable` response (which is different from the `404` one would get by simply using a random URL).

Checkout the `v2` tag, and build the new container:

**NOTE**
> `VERSION` may be different but **must** match the value in `frontend-v2.yaml`


```bash
VERSION=0.6.6 && \
    IMAGE="massenz/simple-flask" && \
    docker build -t $IMAGE:$VERSION -f docker/Dockerfile . && \
    docker push $IMAGE:$VERSION
```
and deploy the new version *alongside* the older one:

    kubectl apply -f configs/frontend-v2.yaml

**NOTE**
> We are **not** executing a rollout deployment of the new version: the point of this exercise is to demonstrate how two distinct versions/deployment of the same service can live alongside the same Kubernetes cluster, and an Ingress controller may be used to direct traffic to the correct one according to a URL pattern.

then expose the `kmaps-v2` service:

    kubectl expose deployment frontend-v2 --port 80 --target-port 8080 \
        --type NodePort --name kmaps-v2

At this point, the new version of the service is reachable via:

    curl -fs http://frontend.info/kmaps/v2
    
and note the returned page is for the new service:

```html
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/html">
  <head lang="en">
    <meta charset="UTF-8">
    <link rel="stylesheet" type="text/css"
          href="/kmaps/v2/static/stylesheet.css">
    <link rel="shortcut icon" href="/kmaps/v2/static/favicon.ico">
    <title>Simple Flask Server</title>
  </head>
  <body>
    <div><img src="/kmaps/v2/static/logo.png" height="42" width="42">
        <h1>KMaps Web Server - v2</h1>
    </div>
    ...
```

It is important to note how the URL had to be "rewritten" so that when the controller rewrites them, the resulting path matches the file location:

        <img src="/kmaps/v2/static/logo.png" height="42" width="42">

was generated in Python dynamically via:

```python
@application.context_processor
def utility_processor():
    url_prefix = application.config['URL_PREFIX']

    def static(resource):
        # `url_for` returns the leading / as it is computed as an absolute path.
        return f"{url_prefix}{url_for('static', filename=resource)}"
    return dict(static_for=static)

```

and the `URL_PREFIX` configuration was obtained via the `ConfigMap` for [`frontend-v2`](configs/frontend-v2.yaml):

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: frontend-config-v2

data:
  config.yaml: |
    server:
      workdir: /var/lib/flask
      url_prefix: /kmaps/v2
      url_v1: /kmaps
...
```

Equally, the link back to `v1` can be provided by dynamically loading it from the same configuration (`url_v1`) in [`index.html`](templates/index.html):

```html
    {% if v1_url %}
    <div>
        <h6>If you prefer you can <a href="{{ v1_url }}">go back to v1</a></h6>
    </div>
    {% endif %}
```
