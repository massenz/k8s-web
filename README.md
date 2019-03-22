# simple-flask

__Version:__ `0.4.0`

Simple [Flask](https://flask.io) server to demonstrate K8s capabilities; run with `--help`
to see the CLI options available.

# Run locally

This uses ['pipenv'](https://docs.pipenv.org) to build a local virtualenv and run the application, see the docs for how to install it (essentially, `brew install pipenv`) then:

    $ pipenv install
    $ pipenv run ./run_server.py [options]

the `install` command is necessary only once, or if you modify the `Pipenv` file to add dependencies.


# Container

This is built as a container:
 
    docker login
    docker build -t massenz/simple-flask:0.5.0 -f docker/Dockerfile .
    docker push massenz/simple-flask:0.5.0

expecting the following `ENV` args:

    ENV DEBUG='' 
        SERVER_PORT=8080 
        SECURE_PORT=8443 
        SECRET='chang3Me'

These can be re-defined either using `--env` with `docker run` or via the usual Kubernets method 
to inject `env` arguments in the template.


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
the K8s DNS will resolve the services (using the `Service`'s `name`):

```bash
$ kubectl exec frontend-cluster-4q8j5 -- \
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

$ kubectl exec -it frontend-cluster-4q8j5 -- \
        curl -X POST -d '{"_id": "100", "name": "Rebo", "job": "Cisco"}' \
          -H "Content-type: application/json" \
          http://frontend/api/v1/entity

{"msg":"inserted"}

$ kubectl exec -it frontend-cluster-4q8j5 -- curl -fs \                      
          -H "Content-type: application/json" \
          http://frontend/api/v1/entity/100

[{"_id": "100", "job": "Cisco", "name": "Rebo"}]
```


# Deploy StatefulSet (Cassandra)

`TODO: this section needs to be reviewed`

See files in the [`cassandra`](configs/cassandra) folder.

    $ kubectl apply -f configs/stateful/test-cluster.yaml

The `cx-svc` service is headless, so it can't be used to connect to the Pods (this is by design; 
each pod is an individual node, and they are not -necessarily- supposed to be load-balanced); to
test use instead the `cqlsh` deployed in each node:

    $ kubectl exec -ti cassandra-0 cqlsh

or we can run a "client" Pod and use it to connect to our Cassandra test cluster:

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
