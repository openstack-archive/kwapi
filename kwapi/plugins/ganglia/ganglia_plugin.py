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

"""Export metrics to Ganglia server."""

import socket
import sys
from kwapi.utils import cfg, log
from ganglia import GMetric

LOG = log.getLogger(__name__)

cfg.CONF(sys.argv[1:],
         project='kwapi',
         default_config_files=['/etc/kwapi/ganglia.conf'])
ganglia_opts = [
    cfg.BoolOpt('signature_checking',
                required=True,
                ),
    cfg.MultiStrOpt('ganglia_server',
               required=True,
               ),
    cfg.MultiStrOpt('watch_probe',
        required=False,
        ),   
    cfg.StrOpt('driver_metering_secret',
               required=True,
               ),
]
cfg.CONF.register_opts(ganglia_opts)
site = socket.getfqdn().split('.')[1]
ganglia = GMetric(cfg.CONF.ganglia_server[0])
ip_probe = {}

def update_rrd(probe, data_type, timestamp, metrics, params):
    """Retrieve hostname and address"""
    if not data_type == 'power':
        return
    probe_site, probe_id = probe.split(".")
    if not probe_id in ip_probe:
        # Hack to know if it is multi-probe
        if probe_id.count('-') > 1:
            # Ignore multi-probe
            return
        hostname = "%s.%s.grid5000.fr" % (probe_id, probe_site)
        ip = socket.gethostbyname(hostname)
        ip_probe[probe_id] = (ip, hostname)
    ganglia.send(
        name='pdu2',
        units='Watts',
        type='uint16',
        value=int(metrics),
        hostname='%s:%s' % (ip_probe[probe_id][0], ip_probe[probe_id][1]),
        spoof=True
    )
    return

