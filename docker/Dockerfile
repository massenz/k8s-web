# Created by M. Massenzio (c) 2018-2019

FROM python:3.7-slim
MAINTAINER Marco Massenzio (marco@alertavert.com)

# TODO: Use K8s Secrets
ENV DEBUG='' SERVER_PORT=8080 SECURE_PORT=8443 SECRET='chang3Me'

WORKDIR /opt/simple

ADD requirements.txt ./
RUN pip install -U pip && \
    pip install -r requirements.txt

ADD templates ./templates/
ADD static ./static/
ADD utils ./utils
ADD sample-config.yaml /etc/flask/config.yaml
ADD application.py run_server.py build.settings ./

EXPOSE ${SERVER_PORT} ${SECURE_PORT}

# "Exec" form of ENTRYPOINT, so we can substitute env values.
# DO NOT use CMD as it will be ignored; also CLI invocations will
# ignore any arguments passed following the container image.
ENTRYPOINT ./run_server.py ${DEBUG} -p ${SERVER_PORT} \
    -s ${SECURE_PORT} --secret-key ${SECRET} --accept-external
