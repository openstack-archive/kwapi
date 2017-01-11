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
import keystoneclient.middleware.auth_token as auth_token
from oslo.config import cfg

from kwapi.openstack.common import policy

_ENFORCER = None
OPT_GROUP_NAME = 'keystone_authtoken'


def register_opts(conf):
    """Registers keystoneclient middleware options."""
    conf.register_opts(auth_token.opts,
                       group=OPT_GROUP_NAME,
                       )
    auth_token.CONF = conf


register_opts(cfg.CONF)


def install(app, conf):
    """Installs ACL check on application."""
    app.wsgi_app = auth_token.AuthProtocol(app.wsgi_app,
                                           conf=dict(conf.get(OPT_GROUP_NAME)))
    app.before_request(check)


def check():
    """Checks application access."""
    headers = flask.request.headers
    global _ENFORCER
    if not _ENFORCER:
        _ENFORCER = policy.Enforcer()
    if not _ENFORCER.enforce('context_is_admin',
                             {},
                             {'roles': headers.get('X-Roles', "").split(",")}):
        return "Access denied", 401
