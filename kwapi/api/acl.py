# -*- coding: utf-8 -*-

"""Set up the ACL to access the API."""

import flask
from keystoneclient.v2_0.client import Client

from kwapi.openstack.common import cfg

acl_opts = [
    cfg.StrOpt('acl_auth_url',
               required=True,
               ),
    ]

cfg.CONF.register_opts(acl_opts)

def install(app):
    """Installs ACL check on application."""
    app.before_request(check)
    return app

def check():
    """Checks application access."""
    headers = flask.request.headers
    try:
        client = Client(token=headers.get('X-Auth-Token'), auth_url=cfg.CONF.acl_auth_url)
    except:
        return "Access denied", 401
    else:
        if not client.authenticate():
            return "Access denied", 401
