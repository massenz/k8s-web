# Created by M. Massenzio (c) 2018

FROM python:3.6
MAINTAINER Marco Massenzio (marco@alertavert.com)

# Override any of these options using --env to enable verbose logging, etc.
ENV VERBOSE='' DEBUG='' WORKDIR=/opt/simple/data SERVER_PORT=8080 SECURE_PORT=8443

WORKDIR /opt/simple
RUN mkdir -p ${WORKDIR}

ADD requirements.txt ./
RUN pip install -U pip
RUN pip install -r requirements.txt

ADD templates ./templates/
ADD utils ./utils
ADD application.py run_server.py ./

EXPOSE ${SERVER_PORT} ${SECURE_PORT}

ENTRYPOINT python run_server.py
CMD ${VERBOSE} ${DEBUG} \
    --workdir ${WORKDIR} \
    -p ${SERVER_PORT} \
    -s ${SECURE_PORT}
