#!/usr/bin/env python
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

import signal
import sys

from kwapi.utils import cfg
import zmq

from kwapi.utils import log

LOG = log.getLogger(__name__)

forwarder_opts = [
    cfg.MultiStrOpt('probes_endpoint',
                    required=True,
                    ),
    cfg.StrOpt('forwarder_endpoint',
               required=True,
               ),
    cfg.StrOpt('log_file',
               required=True,
               ),
]

cfg.CONF.register_opts(forwarder_opts)


def forwarder():
    """Listens probes_endpoints and forwards messages to the plugins."""
    LOG.info('Forwarder listening to %s' % cfg.CONF.probes_endpoint)
    context = zmq.Context.instance()
    frontend = context.socket(zmq.XPUB)
    frontend.bind(cfg.CONF.forwarder_endpoint)
    backend = context.socket(zmq.XSUB)
    for endpoint in cfg.CONF.probes_endpoint:
        backend.connect(endpoint)
    poll = zmq.Poller()
    poll.register(frontend, zmq.POLLIN)
    poll.register(backend, zmq.POLLIN)
    while True:
        items = dict(poll.poll(1000))
        if items.get(backend) == zmq.POLLIN:
            msg = backend.recv_multipart()
            frontend.send_multipart(msg)
        elif items.get(frontend) == zmq.POLLIN:
            msg = frontend.recv()
            backend.send(msg)


def signal_handler(signum, frame):
    """Intercepts TERM signal."""
    if signum is signal.SIGTERM:
        raise KeyboardInterrupt


def start():
    """Starts Kwapi forwarder."""
    cfg.CONF(sys.argv[1:],
             project='kwapi',
             default_config_files=['/etc/kwapi/forwarder.conf']
             )
    log.setup(cfg.CONF.log_file)
    signal.signal(signal.SIGTERM, signal_handler)
    try:
        forwarder()
    except KeyboardInterrupt:
        pass
