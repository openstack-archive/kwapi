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

"""Set up the RRD server application instance."""

import socket
import sys
import thread

import flask
import ast
from execo_g5k import get_g5k_sites

from kwapi.plugins import listen
from kwapi.utils import cfg, log
import live
import v1

LOG = log.getLogger(__name__)

app_opts = [
    cfg.MultiStrOpt('probes_endpoint',
                    required=True,
                    ),
    cfg.IntOpt('rrd_port',
               required=True,
               ),
    cfg.StrOpt('log_file',
               required=True,
               ),
]

cfg.CONF.register_opts(app_opts)


class ReverseProxied(object):
    '''Wrap the application in this middleware and configure the
    front-end server to add these headers, to let you quietly bind
    this to a URL other than / and to an HTTP scheme that is
    different than what is used locally.

    In nginx:
    location /myprefix {
        proxy_pass http://192.168.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Scheme $scheme;
        proxy_set_header X-Script-Name /myprefix;
        }

    :param app: the WSGI application
    '''
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

        scheme = environ.get('HTTP_X_SCHEME', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme

        server = environ.get('HTTP_X_FORWARDED_SERVER', '')
        LOG.info(server)
        if server:
            environ['HTTP_HOST'] = server

        return self.app(environ, start_response)


def make_app():
    """Instantiates Flask app, attaches collector database. """
    LOG.info('Starting LIVE')
    app = flask.Flask(__name__)
    app.wsgi_app = ReverseProxied(app.wsgi_app)
    app.register_blueprint(v1.blueprint)
    app.secret_key = 'kwapi-secret'
    try:
        v1.sites = get_g5k_sites()
    except:
        try:
            v1.sites = ast.literal_eval(cfg.CONF.g5k_sites)
        except:
            v1.sites = []

    thread.start_new_thread(listen, (live.update_probe,))
    live.create_dirs()
    live.create_color_gen()

    hostname = socket.getfqdn().split('.')
    hostname = hostname[1] if len(hostname) >= 2 else hostname[0]

    @app.before_request
    def attach_config():
        flask.request.hostname = hostname
        flask.request.probes_network = live.probes_set_network
        flask.request.probes_power = live.probes_set_power
        flask.request.scales = live.scales
    return app


def start():
    """Starts Kwapi Live."""
    cfg.CONF(sys.argv[1:],
             project='kwapi',
             default_config_files=['/etc/kwapi/live.conf'])
    log.setup(cfg.CONF.log_file)
    root = make_app()
    root.run(host='0.0.0.0', port=cfg.CONF.rrd_port)
