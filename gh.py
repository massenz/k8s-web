#!/usr/bin/env python3


import json

from flask import Flask, request, jsonify, make_response, logging, redirect, url_for
from flask_login import LoginManager, login_required, current_user, login_user, logout_user
from imetrics.registry import global_registry
from imetrics.reporters import HubbleTimedReporter
from requests_oauthlib import OAuth2Session

from login import User

app = Flask('OAuth2 app')
app.config.update(
    USER=None,
    AUTHENTICATED=False,
    TEAM="amp-sre-github",
    SECRET_KEY="azekret"
)
# app.add_url_rule('/favicon.ico',
#                  redirect_to=url_for('static', filename='favicon.ico'))

# TODO: Support Splunk forwarder
log = logging.create_logger(app)
log.setLevel("DEBUG")


# TODO: move to YAML config
client_id = 'b3278dfe64fe2b29277c'
client_secret = '4f5f946f171ae4a46a700cbd8858241befdc091a'

# This MUST be a "sub-path" of the redirect_uri configured in the app settings.
redirect_uri = 'http://localhost:8080/callback'
oauth_url = 'https://github.com/login/oauth/authorize'
token_url = 'https://github.com/login/oauth/access_token'
user_url = 'https://api.github.com/user'
teams_url = 'https://github.com/api/v3/user/teams'
scope = ['user']

github = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)

# Flask-Login implementation
login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = 'login'

# TODO: poor man's database
users_db = dict()


@login_manager.user_loader
def load_user(user_id):
    return users_db.get(user_id)


@app.route("/login", methods=['GET', 'POST'])
def login():
    print("LOGIN")
    print("Args:", request.args)
    auth_url, state = github.authorization_url(oauth_url)

    # TODO: fetch the auth_url in a Browser, which will redirect to the /callback endpoint.
    print("AUTH_URL:", auth_url)
    return redirect(auth_url, code=302)


@app.route("/logout", methods=['GET'])
def logout():
    print("LOGOUT: ", current_user)
    logout_user()
    return redirect(url_for('home'))


@app.route("/", methods=['GET'])
def home():
    return "Login here..."


@app.route('/callback', methods=['GET'])
def oauth_callback():
    print("Query:", request.args)
    print("Headers:", request.headers)

    code = request.args.get('code')
    state = request.args.get('state')
    github.fetch_token(token_url, client_id=client_id, client_secret=client_secret,
                       code=code, state=state)

    # Fetch basic info about the user; see user.json for an example returned value.
    r = github.get(user_url)
    if not r.ok:
        raise ValueError("cannot find user - should return a 403")
    user_data = r.json()

    # Verify that the user is a member of the required TEAM
    r = github.get(teams_url)
    if not r.ok:
        raise ValueError("no teams for user - should return a 403")
    teams_data = r.json()
    for team in teams_data:
        if team['name'] == app.config['TEAM']:
            break
    else:
        raise ValueError("user not a member of tema - should return a 401")

    user_id = user_data['login']
    user = User(user_id, user_data['name'])
    users_db[user_id] = user
    login_user(user)
    return redirect(url_for('welcome'))


@app.route('/welcome', methods=['GET'])
@login_required
def welcome():
    # TODO: render main page
    return f"Welcome, {current_user.name}!"


app.run(port=8080, host="0.0.0.0", debug=True)
