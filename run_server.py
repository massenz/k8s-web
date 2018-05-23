#!/usr/bin/env python
#
# Copyright AlertAvert.com (c) 2013. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import argparse
import json
import pathlib

import yaml

from application import prepare_env, application

__author__ = 'marco'


CONFIG_FILE = pathlib.Path("/etc/flask/config.yaml")


def parse_args():
    """ Parse command line arguments and returns a configuration object
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', help="The port for the server to listen on", type=int,
                        default=5050)

    parser.add_argument('-s', '--secure-port', help="The TLS port for the server to listen on",
                        type=int, default=5443)

    parser.add_argument('-v', '--verbose', action='store_true', help='Enables debug logging')

    parser.add_argument('--debug', action='store_true', help="Turns on debugging/testing mode and "
                                                             "disables authentication")

    parser.add_argument('--secret-key', help='Used by the flask server to encrypt secure cookies')

    parser.add_argument('--workdir', help="Where to store files, must be an absolute path",
                        default='/tmp')

    parser.add_argument('--db_uri', help='The URI to the MongoDB server')
    return parser.parse_args()


def run_server():
    """ Starts the server, after configuring some application values.
        This is **not** executed by the Beanstalk framework

    :return:
    """
    config = parse_args()

    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as cfg:
            app_cfg = yaml.load(cfg)
            print("File Config:\n", json.dumps(app_cfg, indent=4))
    else:
        raise ValueError(f"No configuration file {CONFIG_FILE}")

    prepare_env(config)

    # TODO(marco): enable TLS
    application.run(host='0.0.0.0',
                    debug=config.debug,
                    port=config.port)


if __name__ == '__main__':
    run_server()
