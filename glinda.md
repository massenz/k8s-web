# Glinda / Kubernetes in AWS

## Setup client

See the `kubeconf.us-west-2` config file.

```
export KUBECONFIG=$HOME/.kube/config:$HOME/box/k8s/kubeconf.us-west-2

kubectl config view
kubectl config use-context admin@glinda-aws
kubectl create ns amp

kubectl config set-context $(kubectl config current-context) --namespace=amp
```

## DNS Utils

This is useful to run test when verifying hostnames are resolvable and routable:

```shell
    kubectl run dnsutils --image=massenz/dnsutils:1.0 \
        --generator=run-pod/v1 --command -- sleep infinity
```

the "customized" image adds `curl` to the `dnsutils` container:

    kubectl exec -it dnsutils curl http://192.168.167.223:30395/admin/health

# Deploy service

Follow README in `simple-flask`: [2-tier Service in Kubernetes](#2-tier-service-in-kubernetes).


# Failure:

$ kubectl describe pvc mongodb-pvc
Name:          mongodb-pvc
Namespace:     amp
StorageClass:
Status:        Pending
Volume:
Labels:        <none>
Annotations:   kubectl.kubernetes.io/last-applied-configuration={"apiVersion":"v1","kind":"PersistentVolumeClaim","metadata":{"annotations":{},"name":"mongodb-pvc","namespace":"amp"},"spec":{"accessModes":["ReadWrit...
Finalizers:    [kubernetes.io/pvc-protection]
Capacity:
Access Modes:
Events:
  Type    Reason         Age               From                         Message
  ----    ------         ----              ----                         -------
  Normal  FailedBinding  5s (x21 over 4m)  persistentvolume-controller  no persistent volumes available for this claim and no storage class is set
