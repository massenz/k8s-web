# simple-flask

__Version:__ `0.4.0`

Simple [Flask](https://flask.io) server to demonstrate K8s capabilities; run with `--help`
to see the CLI options available.

# Run locally

This uses ['pipenv'](https://docs.pipenv.org) to build a local virtualenv and run the application, see the docs for how to install it (essentially, `brew install pipenv`) then:

    $ pipenv install
    $ pipenv run ./run_server.py [options]

the `install` command is necessary only once, or if you modify the `Pipenv` file to add dependencies.


# AppleConnect integration

This project uses the [AppleConnect integration library](https://github.pie.apple.com/python-frameworks/flask-appleconnect) to authenticate users.

- to enable the UAT environment in Apple Directory and create an OD Group, see [here](https://connectme.apple.com/docs/DOC-1436323)

- you need to register your app to get an `Application ID`, [see here](https://idms.apple.com/IdmsServiceApp/#/createapp)

- to get an `Application Key` see [here](https://connectme.apple.com/docs/DOC-1138451)


`TODO: is there any way to make the "Return URL" dynamically configurable?`

> Currently, setting up the "service" requires submitting a form with a 3-day delay, so we don't 
know if the tentative implementation in `ac.py` really works (UAT).

### Apple Directory groups

Created the following groups to manage AppleConnect APIs and Hubble integration:

    - pegasus-api-admin     Admin group for all other groups
    - pegasus-api           For AppleConnect integration
    - pegasus-api-dev       Developers group
    - pegasus-api-sre       SRE group
    

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


# 2-tier Service in Kubernetes

Creates a two tier (frontend / backend) service, with the backend running a stateful MongoDB and the Web frontend is ran as a Flask application:

```
  # Authenticate to Registry first
  docker login docker.apple.com

  # Create & Push Docker image for Web app
  docker build -t docker.apple.com/amp-sre/simple-flask:0.3.1 .
  docker push docker.apple.com/amp-sre/simple-flask:0.3.1
```

```
  # Create the Volume claim, and start the DB Pod
  # (which will mount the volume)
  kc apply -f mongo-pvc.yaml
  kc apply -f mongo-pod.yaml
  kc apply -f backend-service.yaml
```
```
  # Create the configuration (mounted as as volume) then start
  # and deploy the frontend service.
  kc create configmap frontend-config -n apps --from-file=config.yaml
  kc apply -f flask-replicas.yaml
  kc apply -f frontend-service.yaml
```
```
  # Verify that the Pods are running
  kc get po -n apps

  # Check out the details on one of them (change the
  # name to the actual pod name)
  kc describe pod frontend-cluster-cpgms -n apps
```

and then to verify:

```
  kc exec -it frontend-cluster-cpgms -n apps /bin/bash

    curl http://localhost:8080/config

    curl -X POST -d '{"_id": "100", "name": "Rebo", "job": "Cisco"}' \
          -H "Content-type: application/json" \
          http://localhost:8080/api/v1/entity

    curl http://localhost:8080/api/v1/entity/100
```

# Deploy StatefulSet (Cassandra)

See files in the [`configs/stateful`](configs/stateful) folder.

The `cx-svc` service is headless, so it can't be used to connect to the Pods (this is by design; 
each pod is an individual node, and they are not -necessarily- supposed to be load-balanced); to
test use instead the `cqlsh` deployed in each node:

    $ kubectl exec -ti cassandra-0 cqlsh

Once we deploy a regular Service:

    $ kubectl apply -f configs/stateless/test-cluster.yaml
    
we can run a "client" Pod and use it to connect to our Cassandra test cluster:

    kc run cqlsh --image=cassandra:3.10 \
        --generator=run-pod/v1 --command -- sleep infinity

and then run CQL commands from its shell, connecting to the service:

    $ kubect exec -ti cqlsh -- cqlsh test-cluster
    Connected to dev_cluster at test-cluster:9042.
    [cqlsh 5.0.1 | Cassandra 3.10 | CQL spec 3.4.4 | Native protocol v4]
    Use HELP for help.
    cqlsh> DESCRIBE KEYSPACEs;
    
    system_schema  system              system_traces
    system_auth    system_distributed  my_keyspace  

or even pipe from a `.cql` file:

    $ kubect exec -ti cqlsh -- cqlsh test-cluster < configs/stateful/user.cql
    
## Reaching individual nodes

K8s sets up SRV records for the nodes in a StatefulSet, using the node name and the
"headless" service name to resolve the FQDNs:

    $ kubect exec -ti dnsutils -- dig SRV cassandra.default.svc.cluster.local               
    ...
    ;; ADDITIONAL SECTION:
    cassandra-0.cassandra.default.svc.cluster.local. 30 IN A 10.1.0.170
    cassandra-1.cassandra.default.svc.cluster.local. 30 IN A 10.1.0.172
    cassandra-2.cassandra.default.svc.cluster.local. 30 IN A 10.1.0.173

Thus:

    $ kubect exec -ti dnsutils -- nslookup cassandra-0.cassandra
    Server:		10.96.0.10
    Address:	10.96.0.10#53
    
    Name:	cassandra-0.cassandra.default.svc.cluster.local
    Address: 10.1.0.170

which in turn means we can use something like this in the Pod definition:

        - name: CASSANDRA_SEEDS
          value: cassandra-0.cassandra

and the nodes in the cluster can find each other.
