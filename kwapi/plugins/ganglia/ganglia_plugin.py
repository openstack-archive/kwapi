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
    cfg.StrOpt('metric_name',
               required=True,
               ),
    cfg.StrOpt('metric_units',
               required=True,
               ),
    cfg.StrOpt('metric_type',
               required=True,
               ),
]
cfg.CONF.register_opts(ganglia_opts)
hostname = socket.getfqdn().split('.')
site = hostname[1] if len(hostname) >= 2 else hostname[0]

ganglia = GMetric(cfg.CONF.ganglia_server[0])
metric_name = cfg.CONF.metric_name
metric_units = cfg.CONF.metric_units
metric_type = cfg.CONF.metric_type
ip_probe = {}

def update_rrd(probe_uid, probes_names, data_type, timestamp, metrics, params):
    """Retrieve hostname and address"""
    if not data_type == 'power':
        return
    if not type(probes_names) == list:
        probes_names= [probes_names]
    if len(probes_names) > 1:
        # Multiprobes are not exported
        return
    for probe in probes_names:
        probe_site = probe.split('.')[0]
        probe_id = str(".".join(probe.split('.')[1:])) 
        if not probe_id in ip_probe:
            hostname = "%s.%s.grid5000.fr" % (probe_id, probe_site)
            try:
                ip = socket.gethostbyname(hostname)
                ip_probe[probe_id] = (ip, hostname)
            except:
                LOG.error("Fail to retrieve %s ip", hostname)
                ip_probe[probe_id] = None
                continue
        if not ip_probe[probe_id]:
            continue
        ganglia.send(
            name=metric_name,
            units=metric_units,
            type=metric_type,
            value=int(metrics),
            hostname='%s:%s' % (ip_probe[probe_id][0], ip_probe[probe_id][1]),
            spoof=True
        )
    return
