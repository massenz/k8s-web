#!/usr/bin/env python3

__author__ = 'M. Massenzio (massenz@adobe.com'

import os

from flask import Flask, redirect, url_for, request, jsonify, make_response, logging

from imetrics.registry import global_registry
from imetrics.reporters import HubbleTimedReporter


app = Flask('my secure app')

# TODO: Support Splunk forwarder
log = logging.create_logger(app)


@app.route("/login", methods=['GET'])
def login(user):
    log.info("HEADERS: %s", request.headers)
    return make_response(jsonify(user))


@app.route("/", methods=['GET'])
def home(user):
    return f"Hello, {user['username']}"


@app.route("/api/v1/envs", methods=['GET'])
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
