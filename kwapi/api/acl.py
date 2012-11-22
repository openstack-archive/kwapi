# -*- coding: utf-8 -*-

"""Set up the ACL to access the API."""

import flask
from keystoneclient.v2_0.client import Client

from kwapi import config

def install(app):
    """Installs ACL check on application."""
    app.before_request(check)
    return app

def check():
    """Checks application access."""
    headers = flask.request.headers
    try:
        client = Client(token=headers.get('X-Auth-Token'), auth_url=config.CONF['acl_auth_url'])
    except:
        return "Access denied", 401
    else:
        if not client.authenticate():
            return "Access denied", 401
