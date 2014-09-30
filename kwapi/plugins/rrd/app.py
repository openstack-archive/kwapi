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

import signal
import socket
import sys
import thread

import flask

from kwapi.plugins import listen
from kwapi.utils import cfg, log
import rrd
import v1

LOG = log.getLogger(__name__)

app_opts = [
    cfg.BoolOpt('visualization',
                required=True,
                ),
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
        LOG.info(script_name)
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

        scheme = environ.get('HTTP_X_SCHEME', '')
        LOG.info(scheme)
        if scheme:
            environ['wsgi.url_scheme'] = scheme

        server = environ.get('HTTP_X_FORWARDED_SERVER', '')
        LOG.info(server)
        if server:
            environ['HTTP_HOST'] = server

        return self.app(environ, start_response)


def make_app():
    """Instantiates Flask app, attaches collector database. """
    LOG.info('Starting RRD')
    app = flask.Flask(__name__)
    app.wsgi_app = ReverseProxied(app.wsgi_app)
    app.register_blueprint(v1.blueprint)

    thread.start_new_thread(listen, (rrd.update_rrd,))
    rrd.create_dirs()

    hostname = socket.getfqdn().split('.')
    hostname = hostname[1] if len(hostname) >= 2 else hostname[0]

    @app.before_request
    def attach_config():
        flask.request.hostname = hostname
        flask.request.probes = rrd.probes_set
        flask.request.scales = rrd.scales
    return app


def start():
    """Starts Kwapi RRD."""
    cfg.CONF(sys.argv[1:],
             project='kwapi',
             default_config_files=['/etc/kwapi/rrd.conf'])
    log.setup(cfg.CONF.log_file)
    if cfg.CONF.visualization:
        root = make_app()
        root.run(host='0.0.0.0', port=cfg.CONF.rrd_port)
    else:
        thread.start_new_thread(listen, (rrd.update_rrd,))
        rrd.create_dirs()
        signal.signal(signal.SIGINT, signal_handler)
        signal.pause()


def signal_handler(signal, frame):
        sys.exit(0)
