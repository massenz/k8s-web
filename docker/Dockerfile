# Copyright (c) 2020 AlertAvert.com  All rights reserved.
# Created by M. Massenzio

FROM python:3.7-slim
MAINTAINER Marco Massenzio (marco@alertavert.com)

ENV DEBUG=""
ENV SERVER_PORT=8080
ENV WORKINGDIR="/var/local/share/k8s-web"
ENV CONFIG="${WORKINGDIR}/config.yaml"

WORKDIR /opt/web

RUN mkdir -p ${WORKINGDIR}
ADD requirements.txt ./
RUN pip install -U pip && \
    pip install -r requirements.txt

ADD app/ ./
ADD build.settings ./

# This is only a placeholder and will only work for local development.
# The actual config.yaml should be installed via a ConfigMap when
# deploying to Kubernetes.
ADD dev-config.yaml ${CONFIG}


EXPOSE ${SERVER_PORT}

# "Exec" form of ENTRYPOINT, so we can substitute env values.
# DO NOT use CMD as it will be ignored; also CLI invocations will
# ignore any arguments passed following the container image.
ENTRYPOINT ./run_server.py ${DEBUG} -p ${SERVER_PORT} \
        --config-file ${CONFIG} --accept-external \
        --workdir ${WORKINGDIR}
