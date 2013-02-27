# -*- coding: utf-8 -*-
#
# Author: François Rossigneux <francois.rossigneux@inria.fr>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Set up the ACL to access the API."""

import flask
from keystoneclient.v2_0.client import Client
from oslo.config import cfg

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
        client = Client(token=headers.get('X-Auth-Token'),
                        auth_url=cfg.CONF.acl_auth_url)
    except:
        return "Access denied", 401
    else:
        if not client.authenticate():
            return "Access denied", 401
