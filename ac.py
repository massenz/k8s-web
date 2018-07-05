#!/usr/bin/env python3

from flask_appleconnect import FlaskAppleConnect
from flask import Flask

app = Flask('my secure app')
app.config.update(
        APPLECONNECT_APPLICATION_ID=136803,
        APPLECONNECT_APPLICATION_ID_KEY='e50262824924a45f90b8645505ebed54514faa43338d6e1ac790537037a63afa',
        APPLECONNECT_APPLICATION_ADMIN_PASSWORD='password',
        APPLECONNECT_ENVIRONMENT=FlaskAppleConnect.TEST_ENVIRONMENT,
        APPLECONNECT_ATTRIBUTES=["prsId", "username"],
        APPLECONNECT_ANONYMOUS_USER=dict(prsId=99, username="anon")
)

appleconnect = FlaskAppleConnect(app)

@app.route("/", methods=['GET'])
@appleconnect.auth(param='appleconnect_user')
def get_home(appleconnect_user):
    return "Hello, {username}".format(username=appleconnect_user['username'])
app.run()
