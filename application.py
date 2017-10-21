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
<<<<<<< HEAD
import re
import time
import uuid
=======
import time
>>>>>>> Added slow query

# Flask imports
from flask import (
    Flask,
    make_response,
    jsonify,
    render_template,
    request)

from utils import choose, SaneBool

# TODO: move all logging configuration into its own logging.conf file
FORMAT = '%(asctime)-15s [%(levelname)s] %(message)s'
DATE_FMT = '%m/%d/%Y %H:%M:%S'

# TODO: These have been moved to the YAML configuration
DATA_UPLOAD_FILE = 'data_upload.log'
ITUNES = "https://mzuserxp.itunes.apple.com/WebObjects/MZUserXP.woa/wa/recordStats"
# TODO: replace the hard-coded hostname string with a dynamic discovery.
LOCAL = "http://mmassenzio-pro.apple.com:{port}/api/1/upload"


#: Flask App, must be global
application = Flask(__name__)


# TODO: read from config.yaml instead
MAX_RETRIES = 30
RETRY_INTERVAL = 1
DEFAULT_NAME = 'migration_logs'

SENSITIVE_KEYS = ('SESSION_COOKIE_DOMAIN', 'SESSION_COOKIE_PATH', 'RUNNING_AS', 'SECRET_KEY')


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
    pattern = re.compile(r'\.{}$'.format(ext))
    files = [f for f in os.listdir(get_workdir()) if os.path.isfile(os.path.join(get_workdir(), f))]
    for fname in files:
        if re.match(pattern=pattern, string=fname):
            return os.path.join(get_workdir(), fname)
    raise FileNotFound("Could not find data file for {}".format(full_name))


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


def get_db_uri():
    """ The URI for the database, if configured.

    :return:  the contents of the --db_uri flag, if available.
    """
    return application.config.get('DB_URI')


#
# Endpoints and Views
#

@application.route('/')
def home():
    return render_template('index.html', workdir=get_workdir(), db_uri=get_db_uri())


@application.route('/health')
def health():
    """ A simple health-chek endpoint (can be used as a heartbeat too).

    :return: a 200 OK status (and echo back the query args)
    """
    return make_response(jsonify({'status': 'ok', 'query_args': request.args}))


@application.route('/slow')
def slow_query():
    sleep_time = request.args.get('q')
    query = 'fast'
    if sleep_time  is not None:
        try:
            sleep_time = int(sleep_time)
        except:
            sleep_time = 10
        logging.debug("Blocking call on /slow query call for {} seconds".format(sleep_time))
        time.sleep(sleep_time)
        query = 'wait for {} sec'.format(sleep_time)
    return make_response(jsonify({'q': query}))

@application.route('/config')
def get_configs():
    """ Configuration values

    :return: a JSON response with the currently configured application values
    """
    configz = {'health': health()}
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


@application.route('/data', methods=['GET', 'HEAD'])
def download_data(ext):
    """ Retrieves the contents of the first file whose extension matches
        the query argument for ```ext```; e.g.::

            /data?ext=json
    """
    file_type = request.args.get('ext', 'json')
    fname = find_first_match(ext=file_type)
    logging.info('Retrieving data for {}'.format(fname))
    response = make_response()
    # TODO: we should really use the correct MIMETYPE here.
    response.headers["Content-Type"] = "application/{}".format(file_type)
    response.data = get_data(fname)
    return response


@application.route('/upload', methods=['GET', 'POST'])
def upload_data():
    if not os.path.exists(get_workdir()):
        msg = "Error: directory {} does not exist on server".format(get_workdir())
        logging.error(msg)
        return make_response(msg, 404)

    data_file = os.path.join(get_workdir(), DATA_UPLOAD_FILE)
    logging.info("Writing data to {}".format(data_file))
    with open(data_file, 'a') as data:
        data.write("--- {timestamp} ---\n".format(timestamp=datetime.datetime.now().isoformat()))
        for key in request.args.keys():
            value = request.args.get(key)
            data.write("{key}: {value}\n".format(key=key, value=value))
    return make_response('Data received and saved', 200)


@application.route('/timeout/<seconds>')
def timeout(seconds):
    logging.warning("Sleeping for {} seconds".format(seconds))
    time.sleep(float(seconds))
    logging.warning("Sleep ends")
    return make_response('ok', 200)


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
    prepare_env()


def prepare_env(config=None):
    """ Initializes the application configuration

    Must take into account that it may be started locally (via a command-line options) or
    remotely via AWS Beanstalk (in which case only the OS Env variables will be available).

    :param config: an optional L{Namespace} object, obtained from parsing the options
    :type config: argparse.Namespace or None
    """
    if not application.config.get('INITIALIZED'):
        # app_config['RUNNING_AS'] = choose('USER', '', config)
        verbose = SaneBool(choose('FLASK_DEBUG', False, config, 'verbose'))

        # Loggin configuration
        # TODO: move to a loogin.yaml configuration with proper handlers and loggers configuration
        loglevel = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(format=FORMAT, datefmt=DATE_FMT, level=loglevel)

        # Flask apparently does not store this internally.
        application.config['PORT'] = config.port

        # Flask application configuration
        application.config['DEBUG'] = SaneBool(choose('FLASK_DEBUG', False, config, 'debug'))
        application.config['TESTING'] = choose('FLASK_TESTING', False)
        application.config['SECRET_KEY'] = choose('FLASK_SECRET_KEY', 'd0n7useth15', config,
                                                  'secret_key')
        application.config['WORKDIR'] = choose('FLASK_WORKDIR', '/tmp', config, 'workdir')

        application.config['INITIALIZED'] = True
        application.config['DB_URI'] = choose('DB_URI', '', config, 'db_uri')
