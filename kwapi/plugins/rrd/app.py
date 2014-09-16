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

from kwapi.plugins import listen
from kwapi.utils import cfg, log
from time import sleep
import rrd

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

def make_app():
    """Attaches collector database. """
    LOG.info('Starting RRD')

    thread.start_new_thread(listen, (rrd.update_rrd,))
    rrd.create_dirs()

    hostname = socket.getfqdn().split('.')
    hostname = hostname[1] if len(hostname) >= 2 else hostname[0]

def start():
    """Starts Kwapi RRD."""
    cfg.CONF(sys.argv[1:],
             project='kwapi',
             default_config_files=['/etc/kwapi/rrd.conf'])
    log.setup(cfg.CONF.log_file)
    make_app()
    while True:
        try:
            sleep(1)
        except KeyboardInterrupt:
            pass
