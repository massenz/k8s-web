# Created by M. Massenzio (c) 2018

FROM python:3.6
MAINTAINER Marco Massenzio (marco@alertavert.com)

# Override any of these options using --env to enable verbose logging, etc.
# TODO: figure out how to pass the Secret via k8s
ENV DEBUG='' SERVER_PORT=8080 SECURE_PORT=8443 SECRET='chang3Me'

WORKDIR /opt/simple

ADD requirements.txt ./
RUN pip install -U pip
RUN pip install -r requirements.txt

ADD templates ./templates/
ADD utils ./utils
ADD application.py run_server.py ./

EXPOSE ${SERVER_PORT} ${SECURE_PORT}

# "Exec" form of ENTRYPOINT, so we can substitute env values.
# DO NOT use CMD as it will be ignored; also CLI invocations will
# ignore any arguments passed following the container image.
ENTRYPOINT python run_server.py ${DEBUG} -p ${SERVER_PORT} \
    -s ${SECURE_PORT} --secret-key ${SECRET}
