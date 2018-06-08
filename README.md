# simple-flask

__Version:__ `0.3.1`

Simple [Flask](https://flask.io) server to demonstrate K8s capabilities; run with `--help`
to see the CLI options available.

# Container

This is built as a container (currently pushed to
[`massenz/simple-flask`](https://hub.docker.com/r/massenz/simple-flask)), with the following ENV
args:

    ENV VERBOSE=''
        DEBUG=''
        WORKDIR=/opt/simple/data
        SERVER_PORT=8080
        SECURE_PORT=8443


# Kubernetes

First create the internal service (Load Balances the `ReplicaSet` started below):

  kubectl create -f frontend-service.yaml

and an external service (via `Endpoints`):

  kubectl create -f cassandra-endpoints.yaml
  kubectl create -f cassandra-service.yaml

Now deploy the "cluster":

  kubectl create -f flask-replicas.yaml
  kubectl get pods

Inside the PODs, several `Env` variables will point to various services; however,
the K8s DNS will resolve the services (using the `Service`'s `name`):

  kubectl exec frontend-cluster-9wqll -- \
    curl -v http://frontend/config | python -m json.tool

the `cassandra` service will be reachable at the following URI: `tcp://cassandra:9042`.

## ConfigMaps

The `config.yaml` file is used as a [ConfigMap](https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap/) to run the server in k8s:

  kubectl create configmap frontend-config --from-file=config.yaml
