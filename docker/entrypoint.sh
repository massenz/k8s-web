#!/usr/bin/env bash
#
# entrypoint.sh
# See: https://codetrips.com/2021/03/31/docker-entrypoint-and-a-note-about/

set -e

cmd="./run_server.py ${DEBUG} -p ${SERVER_PORT} \
        --config ${CONFIG} --accept-external \
        --workdir ${WORKINGDIR}"

echo $cmd
eval $cmd "$@"
