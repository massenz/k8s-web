#!/usr/bin/env python


import argparse

from application import server
from utils.prepare import prepare_env


def parse_args():
    """ Parse command line arguments and returns a configuration object """
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', help="The port for the server to listen on", type=int,
                        default=5050)

    parser.add_argument('--debug', action='store_true', help="Turns on debugging/testing mode and "
                                                             "disables authentication")

    parser.add_argument('--tls', action='store_true', help="If set, enables TLS connectivity")
    parser.add_argument('--tls-ca-file', help="The location of the CA Bundle")
    parser.add_argument('--tls-allow-invalid', action='store_true',
                        help="If set, allows TLS connectivity, even if certificates do not "
                             "validate; use ONLY for development/testing")

    parser.add_argument('--accept-external', action='store_const', const='0.0.0.0',
                        help="By default the server will only accept incoming connections from "
                             "`localhost`; if this flag is set, it will accept incoming "
                             "connections from all available NICs")

    parser.add_argument('--secret-key', help='Used by the flask server to encrypt secure cookies')
    parser.add_argument('--db-uri', help='MongoDB URI')
    parser.add_argument('--opa-server',
                        help='Server address for the OPA server, in `host:port` form')

    parser.add_argument('--workdir', help='The application working directory')

    parser.add_argument('--config', help=f'Location of the YAML file with configuration values')

    return parser.parse_args()


def run_server():
    """ Starts the server, after configuring some application values.
        This is **not** executed by the Beanstalk framework

    :return:
    """
    config = parse_args()
    prepare_env(server, config=config)
    server.run(host=config.accept_external,
               debug=config.debug,
               port=config.port)


if __name__ == '__main__':
    try:
        run_server()
    except KeyboardInterrupt:
        print("Terminated by user")
    except Exception as ex:
        print(f"[ERROR] Unexpected error: {ex}")
