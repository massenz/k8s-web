#!/usr/bin/env python3

__author__ = 'M. Massenzio (mmassenzio@apple.com'

import os

from flask_appleconnect import FlaskAppleConnect
from flask import Flask, redirect, url_for, request, jsonify, make_response, logging

from imetrics.registry import global_registry
from imetrics.reporters import HubbleTimedReporter


app = Flask('my secure app')
app.config.update(
        APPLECONNECT_APPLICATION_ID=136803,
        APPLECONNECT_APPLICATION_ID_KEY='e50262824924a45f90b8645505ebed54514faa43338d6e1ac790537037a63afa',
        APPLECONNECT_APPLICATION_ADMIN_PASSWORD='password',
        APPLECONNECT_ENVIRONMENT=FlaskAppleConnect.TEST_ENVIRONMENT,
        APPLECONNECT_RETURN_PATH='/authenticated',
        APPLECONNECT_ATTRIBUTES=["prsId", "username"],
        APPLECONNECT_ANONYMOUS_USER=dict(prsId=99, username="anon"),
)
appleconnect = FlaskAppleConnect(app)

# TODO: Support Splunk forwarder
log = logging.create_logger(app)

# Hubble support
registry = global_registry()
reporter = HubbleTimedReporter(registry, "http://vp00-itunes-hubblehttp.apple.com", 8500,
                               "pegasus.api-server", 30)

qc = registry.counter("queries.counter")


@app.route("/login", methods=['GET'])
@appleconnect.auth(param='appleconnect_user')
def login(appleconnect_user):
    log.info("HEADERS: %s", request.headers)
    return make_response(jsonify(appleconnect_user))


@app.route("/", methods=['GET'])
@appleconnect.auth(param='user')
def home(user):
    return f"Hello, {user['username']}"


@app.route("/api/v1/envs", methods=['GET'])
@appleconnect.auth()
def envs():
    qc.inc()
    return make_response(jsonify({"name": "foo", "vale": "bar"}))


@app.route('/callback', methods=['GET'])
def oauth_callback():
    print("Query:", request.args)
    print("Headers:", request.headers)

    return make_response(jsonify({"status": "ok"}))


@app.route('/welcome', methods=['GET'])
def welcome():
    print("Query:", request.args)
    print("Headers:", request.headers)

    return "Welcome!"


app.run(port=8080, host="0.0.0.0", debug=True)
