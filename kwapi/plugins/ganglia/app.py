# -*- coding: utf-8 -*-
#
# Author:  <francois.rossigneux@inria.fr>
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

from kwapi.plugins import listen
from kwapi.utils import cfg, log
import ganglia_plugin

LOG = log.getLogger(__name__)

app_opts = [
    cfg.MultiStrOpt('probes_endpoint',
                    required=True,
                    ),
    cfg.StrOpt('log_file',
               required=True,
               ),
]

cfg.CONF.register_opts(app_opts)

def start():
    """Starts Kwapi Ganglia."""
    cfg.CONF(sys.argv[1:],
             project='kwapi',
             default_config_files=['/etc/kwapi/ganglia.conf'])
    log.setup(cfg.CONF.log_file)
    thread.start_new_thread(listen, (ganglia_plugin.update_rrd,))
    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()


def signal_handler(signal, frame):
        sys.exit(0)
