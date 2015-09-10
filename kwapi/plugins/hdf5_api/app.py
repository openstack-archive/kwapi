# -*- coding: utf-8 -*-
#
# Author: Clement Parisot <clement.parisot@inria.fr>
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

"""Set up the HDF5 API instance."""

import sys, signal
import thread
from threading import Thread

import flask
from kwapi.plugins import listen
from kwapi.utils import cfg, log
from hdf5_collector import HDF5_Collector
import hdf5_collector
import v1

LOG = log.getLogger(__name__)

app_opts = [
    cfg.MultiStrOpt('probes_endpoint',
                    required=True,
                    ),
    cfg.StrOpt('hdf5_port',
               required=True,
               ),
    cfg.StrOpt('log_file',
               required=True,
               ),
]

cfg.CONF.register_opts(app_opts)

writters = []
def make_app():
    """Instantiates Flask app, attaches collector database. """
    LOG.info('Starting HDF5 API')
    app = flask.Flask(__name__)
    app.register_blueprint(v1.blueprint, url_prefix='')
    storePower = HDF5_Collector('power')
    storeNetworkIn = HDF5_Collector('network_in')
    storeNetworkOut = HDF5_Collector('network_out')
    thread.start_new_thread(listen, (hdf5_collector.update_hdf5,))

    @app.before_request
    def attach_config():
        flask.request.storePower = storePower
        flask.request.storeNetworkIn = storeNetworkIn
        flask.request.storeNetworkOut = storeNetworkOut

    return app

def signal_handler(signal, frame):
    sys.exit(0)

def start():
    """Starts Kwapi HDF5 API."""
    cfg.CONF(sys.argv[1:],
             project='kwapi',
             default_config_files=['/etc/kwapi/hdf5.conf'])
    log.setup(cfg.CONF.log_file)
    signal.signal(signal.SIGINT, signal_handler)
    root = make_app()
    root.run(host='0.0.0.0', port=cfg.CONF.hdf5_port)
    signal.pause()
