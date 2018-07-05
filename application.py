# Copyright AlertAvert.com (c) 2013. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Standard imports
import argparse
import datetime
import logging
import os
import pathlib
import re
import time

# Flask imports
import pymongo
import yaml
from flask import (
    Flask,
    make_response,
    jsonify,
    render_template,
    request,
)

from utils import choose, SaneBool

__author__ = 'M. Massenzio (marco@alertavert.com'


# TODO: move all logging configuration into its own logging.conf file
FORMAT = '%(asctime)-15s [%(levelname)s] %(message)s'
DATE_FMT = '%m/%d/%Y %H:%M:%S'

application = Flask(__name__)


# TODO: read from config.yaml instead
MAX_RETRIES = 30
RETRY_INTERVAL = 1
DEFAULT_NAME = 'migration_logs'

SENSITIVE_KEYS = (
    'SESSION_COOKIE_DOMAIN',
    'SESSION_COOKIE_PATH',
    'RUNNING_AS',
    'SECRET_KEY',
)


class ResponseError(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


class NotAuthorized(ResponseError):
    status_code = 401


class UuidNotValid(ResponseError):
    status_code = 406


class FileNotFound(ResponseError):
    status_code = 404


def get_workdir():
    workdir = application.config.get('WORKDIR')
    if not workdir or not os.path.isabs(workdir):
        raise ResponseError('{0} not an absolute path'.format(workdir))
    return workdir


def build_fname(migration_id, ext):
    workdir = get_workdir()
    timestamp = datetime.datetime.now().isoformat()
    # Remove msec part and replace colons with dots (just to avoid Windows stupidity)
    prefix = timestamp.rsplit('.')[0].replace(':', '.')
    return os.path.join(workdir, migration_id, '{prefix}_{name}.{ext}'.format(
        prefix=prefix, name=DEFAULT_NAME, ext=ext))


def find_first_match(ext):
    """ Returns the first file matching the given extension.

    :param ext: the file extension
    :return: the most recent filename that matches the ID and extension
    :raises: FileNotFound if the file does not exist
    """
    pattern = re.compile(r'\.{ext}$'.format(ext=ext))
    files = [f for f in os.listdir(get_workdir()) if os.path.isfile(os.path.join(get_workdir(), f))]
    for fname in files:
        if re.match(pattern=pattern, string=fname):
            return os.path.join(get_workdir(), fname)
    raise FileNotFound("Could not find any file whose extension matches '{}'".format(ext))


def get_data(fname):
    """ Reads the file and returns its contents.

    :param fname: the name of the file to read.
    :return: the contents of the file.
    :raises FileNotFound: if the file does not exist.
    """
    if not os.path.exists(fname):
        raise FileNotFound("Could not find {name}".format(name=fname))
    with open(fname, 'r') as data:
        return data.read()

# Endpoints and Views


@application.route('/')
def home():
    return render_template('index.html', workdir=get_workdir())


@application.route('/health')
def health():
    """ A simple health-chek endpoint (can be used as a heartbeat too).

    :return: a 200 OK status (and echo back the query args)
    """
    return make_response(jsonify({'status': 'ok'}))


@application.route('/demo')
def demo():
    return make_response(jsonify({'status': 'ok', 'query_args': request.args}))


@application.route('/config')
def get_configs():
    """ Configuration values

    :return: a JSON response with the currently configured application values
    """
    configz = {'health': 'UP'}
    is_debug = application.config.get('DEBUG')
    for key in application.config.keys():
        # In a non-debug session, sensitive config values are masked
        # TODO: it would be probably better to hash them (with a secure hash such as SHA-256)
        # using the application.config['SECRET_KEY']
        if not is_debug and key in SENSITIVE_KEYS:
            varz = "*******"
        else:
            varz = application.config.get(key)
        # Basic types can be sent back as they are, others need to be converted to strings
        if varz is not None and not (isinstance(varz, bool) or isinstance(varz, int)):
            varz = str(varz)
        configz[key.lower()] = varz
    return make_response(jsonify(configz))


@application.route('/api/v1/entity/<id>')
def get_entity(id):
    """Tries to connect to the db and retrieve the entity show ID is `id`"""
    # TODO: Move to a DAO class
    client = pymongo.MongoClient(application.config['DB_URI'])
    db = client.get_database()
    coll = db.get_collection(application.config['DB_COLLECTION'])
    cursor = coll.find({'_id': id})
    result = []
    for item in cursor:
        result.append(item)

    return make_response(jsonify(result))


@application.route('/api/v1/entity', methods=['POST'])
def create_entity():
    """Tries to connect to the db and retrieve the entity show ID is `id`"""
    # TODO: Move to a DAO class
    client = pymongo.MongoClient(application.config['DB_URI'])
    db = client.get_database()
    coll = db.get_collection(application.config['DB_COLLECTION'])
    res = coll.insert_one(request.json)
    response = make_response(jsonify({"msg": "inserted"}))
    response.status_code = 201
    response.headers['Location'] = f'/api/v1/entity/{res.inserted_id}'
    return response


@application.route('/statuscode/<code>')
def statuscode(code):
    logging.info("Returning code".format(code))
    if code == "666":
        raise RuntimeError("Failure!")
    return make_response('Returning status: {}'.format(code), int(code))


@application.errorhandler(ResponseError)
def handle_invalid_usage(error):
    logging.error(error.message)
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@application.before_first_request
def config_app():
    pass


def prepare_env(config=None):
    """ Initializes the application configuration

    :param config: the L{Namespace} object, obtained from parsing the options
    :type config: argparse.Namespace or None
    """
    application.config['RUNNING_AS'] = os.getenv('USER', 'unknown')
    debug = SaneBool(choose('FLASK_DEBUG', False, config, 'debug'))
    application.config['DEBUG'] = debug

    loglevel = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(format=FORMAT, datefmt=DATE_FMT, level=loglevel)

    # Flask apparently does not store this internally.
    application.config['PORT'] = config.port
    application.config['SECURE_PORT'] = config.secure_port

    # Flask application configuration
    application.config['TESTING'] = choose('FLASK_TESTING', False)
    application.config['SECRET_KEY'] = choose('FLASK_SECRET_KEY', 'd0n7useth15', config,
                                              'secret_key')
    application.config['WORKDIR'] = choose('FLASK_WORKDIR', '/tmp', config, 'workdir')

    if not config.config_file:
        raise ValueError("A configuration file MUST be provided, use --config-file")
    config_file = pathlib.Path(config.config_file)
    if not config_file.exists():
        raise FileNotFound(f"Configuration file {config_file} does not exist")

    with open(config_file, 'r') as cfg:
        configs = yaml.load(cfg)
        application.config['DB_URI'] = configs['db']['uri']
        application.config['DB_COLLECTION'] = configs['db']['collection']
