# Created by M. Massenzio (c) 2018-2019

FROM python:3.7-slim
MAINTAINER Marco Massenzio (marco@alertavert.com)

ENV DEBUG='' SERVER_PORT=8080 WORKINGDIR='/var/local/share/k8s-web'

WORKDIR /opt/web

RUN mkdir -p ${WORKINGDIR}
ADD requirements.txt ./
RUN pip install -U pip && \
    pip install -r requirements.txt

ADD app/ ./
ADD config.yaml /etc/flask/config.yaml
ADD build.settings ./


EXPOSE ${SERVER_PORT}

# "Exec" form of ENTRYPOINT, so we can substitute env values.
# DO NOT use CMD as it will be ignored; also CLI invocations will
# ignore any arguments passed following the container image.
ENTRYPOINT ./run_server.py ${DEBUG} -p ${SERVER_PORT} --accept-external
