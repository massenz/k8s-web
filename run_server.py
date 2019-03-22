#!/usr/bin/env python


import argparse
import pathlib

from application import prepare_env, application, ResponseError

CONFIG_FILE = pathlib.Path("/etc/flask/config.yaml")


def parse_args():
    """ Parse command line arguments and returns a configuration object """
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', help="The port for the server to listen on", type=int,
                        default=5050)

    parser.add_argument('-s', '--secure-port', help="The TLS port for the server to listen on",
                        type=int, default=5443)

    parser.add_argument('--debug', action='store_true', help="Turns on debugging/testing mode and "
                                                             "disables authentication")

    parser.add_argument('--accept-external', action='store_const', const='0.0.0.0',
                        help="By default the server will only accept incoming connections from "
                             "`localhost`; if this flag is set, it will accept incoming "
                             "connections from all available NICs")

    parser.add_argument('--secret-key', help='Used by the flask server to encrypt secure cookies')

    parser.add_argument('--config-file', default=CONFIG_FILE,
                        help=f'Location of the YAML file with configuration values; by default, '
                             f'{CONFIG_FILE}')

    return parser.parse_args()


def run_server():
    """ Starts the server, after configuring some application values.
        This is **not** executed by the Beanstalk framework

    :return:
    """
    config = parse_args()
    prepare_env(config)

    # TODO(marco): enable TLS
    application.run(host=config.accept_external,
                    debug=config.debug,
                    port=config.port)


if __name__ == '__main__':
    try:
        run_server()
    except KeyboardInterrupt:
        print("Terminated by user")
    except ResponseError as error:
        print(f"[ERROR] Response error: {error.message}")
    except Exception as ex:
        print(f"[ERROR] Unexpected error: {ex}")
