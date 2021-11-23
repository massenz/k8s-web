import logging
import os
import pathlib
import uuid

import yaml

from utils import SaneBool, choose, FORMAT, DATE_FMT, DEFAULT_MONGODB_URI, version


def create_random_key():
    return str(uuid.uuid4())[:12]


def prepare_env(server, config=None):
    """ Initializes the application configuration

    :param server: the Flask server that we will configure
    :type server: L{flask.Flask}

    :param config: the L{Namespace} object, obtained from parsing the options
    :type config: argparse.Namespace or None
    """
    file_args = {}
    if config.config:
        config_file = pathlib.Path(config.config)
        if config_file.exists():
            with config_file.open('r') as cfg:
                file_args = yaml.safe_load(cfg)
        else:
            print(f"[WARN] Missing configuration file {config_file.absolute()}, using defaults")

    debug = SaneBool(choose('FLASK_DEBUG', file_args.get('debug', False), config, 'debug'))
    loglevel = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(format=FORMAT, datefmt=DATE_FMT, level=loglevel)

    # The CLI args (in the `config` dict) take precedence over the configuration file (`file_args`)
    configs = {

        'DEBUG': debug,
        'PORT': choose('FLASK_PORT', file_args.get('port', 6060), config, 'port'),
        'TESTING': choose('FLASK_TESTING', False),
        'SECRET_KEY': choose('FLASK_SECRET_KEY', file_args.get('secret-key', create_random_key()),
                             config, 'secret_key'),
        'VERSION': version(),

        'RUNNING_AS': choose('USER', 'unknown'),
        'WORKDIR': choose('SERVER_WORKDIR', file_args.get('workdir', '/tmp'), config, 'workdir'),

        'DB_URI': choose('MONGO_DB_URI', file_args.get('db-uri', DEFAULT_MONGODB_URI),
                         config, 'db_uri'),
        'DB_COLLECTION': file_args.get('collection', 'simple-data'),

        'TLS': SaneBool(choose('MONGO_TLS', file_args.get('tls'), config, 'tls')),
        'TLS_CA_FILE': choose('MONGO_TLS_CA_FILE', file_args.get('tls-ca-file'),
                              config, 'tls_ca_file'),
        'TLS_ALLOW_INVALID': choose('MONGO_TLS_ALLOW_INVALID', file_args.get('tls-allow-invalid'),
                                    config, 'tls_allow_invalid') is not None,
    }
    for k, v in configs.items():
        server.config[k] = v
