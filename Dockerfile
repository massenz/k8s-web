# Created by M. Massenzio (c) 2018

FROM python:3.6
MAINTAINER Marco Massenzio (marco@alertavert.com)

# Override any of these options using --env to enable verbose logging, etc.
ENV VERBOSE='' DEBUG='' WORKDIR=/opt/simple/data

WORKDIR /opt/simple
RUN mkdir -p ${WORKDIR}

ADD requirements.txt ./
RUN pip install -r requirements.txt

ADD templates ./templates/
ADD utils ./utils
ADD application.py run_server.py ./

EXPOSE 5050
CMD python run_server.py $VERBOSE $DEBUG --workdir $WORKDIR -p 5050
