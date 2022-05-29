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

__author__ = 'M. Massenzio (marco@alertavert.com)'

import logging
import os
import random
import requests

import pymongo
from bson import ObjectId
from bson.errors import InvalidId
from flask import (
    Flask,
    make_response,
    jsonify,
    render_template,
    request,
    url_for,
    send_from_directory,
)

from utils import version, MONGO_HEALTH_KEYS

server = Flask(__name__)


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


class NotFound(ResponseError):
    status_code = 404


def get_workdir():
    workdir = server.config.get('WORKDIR')
    if not workdir or not os.path.isabs(workdir):
        raise ResponseError(f"{workdir} is not an absolute path")
    return workdir


# Context Processor for Template
@server.context_processor
def utility_processor():
    url_prefix = server.config.get('URL_PREFIX', '')

    def static(resource):
        # `url_for` returns the leading / as it is computed as an absolute path.
        return f"{url_prefix}{url_for('static', filename=resource)}"

    return dict(static_for=static)


# Endpoints and Views
@server.route('/')
def home():
    return render_template('index.html',
                           workdir=get_workdir(),
                           version=version(),
                           v1_url=server.config.get('URL_V1', '/v1/api'))


@server.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(server.root_path, 'static'),
                               'favicon.png', mimetype='image/vnd.microsoft.icon')


@server.route('/health')
def health():
    """ A simple health-chek endpoint

    As this will be used as a heartbeat too (e.g., by the "liveness" probe in Kubernetes) this
    tries to be as fast as possible, and consume the least amount of system resources (thus
    returning a string instead of "jsonifying" it).

    :return: 200 OK status if the server responds at all
    """
    return '{"status": "UP"}'


@server.route('/ready')
def ready():
    """ A readiness endpoint, checks on DB health too.

    :return: a 200 OK status if this server is up, and the backing DB is ready too; otherwise, a
             503 "Temporarily unavailable."
    """
    try:
        # TODO: Move to a DAO class
        client = get_mongo_client()
        info = {}
        for key in MONGO_HEALTH_KEYS:
            info[key] = client.server_info().get(key, "null")
        if info.get("ok") == 1:
            info["status"] = "UP"
        else:
            info["status"] = "WARN"
    except pymongo.errors.ServerSelectionTimeoutError as ex:
        info = {"status": "DOWN", "error": str(ex)}
    response = make_response(jsonify({'status': 'UP', "mongo": info}))
    if info['status'] != "UP":
        response.status_code = 503
    return response


@server.route('/config')
def get_configs():
    """ Configuration values

    :return: a JSON response with the currently configured application values
    """
    configz = {
        'health': 'UP',
        'cookies': request.cookies
    }
    is_debug = server.config.get('DEBUG')
    for key in server.config.keys():
        # In a non-debug session, sensitive config values are masked
        # TODO: it would be probably better to hash them (with a secure hash such as SHA-256)
        # using the application.config['SECRET_KEY']
        if not is_debug and key in SENSITIVE_KEYS:
            varz = "*******"
        else:
            varz = server.config.get(key)
        # Basic types can be sent back as they are, others need to be converted to strings
        if varz is not None and not (isinstance(varz, bool) or isinstance(varz, int)):
            varz = str(varz)
        configz[key.lower()] = varz
    response = make_response(jsonify(configz))
    randval = random.randint(1000, 9999)
    server.logger.info(f"Setting cookie value to {randval}")
    response.set_cookie('y-track', value=f"config-tracker-{randval}", path="/config")
    return response


@server.route('/api/v1/entity/<id>')
def get_entity(id):
    """Tries to connect to the db and retrieve the entity show ID is `id`"""
    # TODO: Move to a DAO class
    client = get_mongo_client()
    db = client.get_database()
    coll = db.get_collection(server.config['DB_COLLECTION'])
    try:
        oid = ObjectId(id)
    except InvalidId as error:
        raise UuidNotValid(str(error))
    result = coll.find_one(oid)
    if not result:
        raise NotFound(f"Entity with ID {id} could not be found")
    result["id"] = str(result.pop("_id"))
    return make_response(jsonify(result))


@server.route('/api/v1/entity')
def get_all_entities():
    """Retrieves all entities from the Db"""
    client = get_mongo_client()
    db = client.get_database()
    coll = db.get_collection(server.config['DB_COLLECTION'])
    results = coll.find()
    response = []
    for result in results:
        result["id"] = str(result.pop("_id"))
        response.append(result)
    return make_response(jsonify(response))


# TODO: update the TLS configuration to be configurable via CLI args.
def get_mongo_client():
    tls = server.config.get('TLS', False)
    connection_params = {
        'tls': tls,
        'serverSelectionTimeoutMS': 250
    }
    if tls:
        connection_params['tlsAllowInvalidCertificates'] = server.config['TLS_ALLOW_INVALID']
        connection_params['tlsCAFile'] = server.config['TLS_CA_FILE']
    return pymongo.MongoClient(server.config['DB_URI'], **connection_params)


@server.route('/api/v1/entity', methods=['POST'])
def create_entity():
    """Creates a new entity in the DB, and returns its URI in the `Location` header"""
    # TODO: Move to a DAO class
    client = get_mongo_client()
    db = client.get_database()
    coll = db.get_collection(server.config['DB_COLLECTION'])
    res = coll.insert_one(request.json)
    response = make_response(jsonify({
        "msg": "inserted",
        "id": f"{res.inserted_id}"
    }))
    response.status_code = 201
    response.headers['Location'] = f'/api/v1/entity/{res.inserted_id}'
    return response


@server.route('/opa/<policy>', methods=['POST'])
def send_policy(policy):
    """Posts a Policy to the OPA Server and returns the result"""
    endpoint = f"http://{server.config['OPA_SERVER']}/v1/data/{policy}"
    opa_result = requests.post(endpoint, json={"input":request.json})
    response = make_response(jsonify({
        "policy_endpoint": endpoint,
        "sent": request.json,
        "result": opa_result.json().get("result")
    }))
    return response


@server.route('/statuscode/<code>')
def statuscode(code):
    logging.info(f"Returning code {code}")
    if code == "666":
        raise RuntimeError("Failure!")
    try:
        return make_response(jsonify({"status": code}), int(code))
    except ValueError:
        raise ResponseError(f"{code} is not a valid integer status code")


@server.errorhandler(ResponseError)
def handle_invalid_usage(error):
    logging.error(error.message)
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@server.errorhandler(404)
def handle_notfound(error):
    message = f"The path `{request.path}` was not found on this server [{request.url}]"
    logging.error(error)
    return message, 404


@server.before_first_request
def config_app():
    pass
