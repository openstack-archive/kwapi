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

"""Set up the HDF5 server application instance."""

import sys
import thread

import flask
from kwapi.plugins import listen
from kwapi.utils import cfg, log
import v1
import hdf5


LOG = log.getLogger(__name__)

app_opts = [
    cfg.MultiStrOpt('probes_endpoint',
                    required=True,
                    ),
    cfg.IntOpt('hdf5_port',
               required=True,
               ),
    cfg.StrOpt('log_file',
               required=True,
               ),
]

cfg.CONF.register_opts(app_opts)


def make_app():
    """Instantiates Flask app, attaches collector database. """
    LOG.info('Starting HDF5')
    app = flask.Flask(__name__)
    app.register_blueprint(v1.blueprint, url_prefix='')

    hdf5.create_dir()
    thread.start_new_thread(listen, (hdf5.update_hdf5,))

    return app


def start():
    """Starts Kwapi HDF5."""
    cfg.CONF(sys.argv[1:],
             project='kwapi',
             default_config_files=['/etc/kwapi/hdf5.conf'])
    log.setup(cfg.CONF.log_file)
    root = make_app()
    root.run(host='0.0.0.0', port=cfg.CONF.hdf5_port)
