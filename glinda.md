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

Follow README in `simple-flask`: [2-tier Service in Kubernetes](README.md/#2-tier-service-in-kubernetes).

