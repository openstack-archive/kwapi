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

import json

import zmq
import ast

from kwapi import security
from kwapi.utils import cfg, log

LOG = log.getLogger(__name__)


def listen(function):
    """Subscribes to ZeroMQ messages, and adds received measurements to the
    database. Messages are dictionaries dumped in JSON format.

    """
    LOG.info('Listening to %s' % cfg.CONF.probes_endpoint)

    context = zmq.Context.instance()
    subscriber = context.socket(zmq.SUB)
    if not cfg.CONF.watch_probe:
        subscriber.setsockopt(zmq.SUBSCRIBE, '')
    else:
        for probe in cfg.CONF.watch_probe:
            subscriber.setsockopt(zmq.SUBSCRIBE, probe + '.')
    for endpoint in cfg.CONF.probes_endpoint:
        subscriber.connect(endpoint)

    while True:
        [probe, message] = subscriber.recv_multipart()
        measurements = json.loads(message)
        if not isinstance(measurements, dict):
            LOG.error('Bad message type (not a dict)')
        elif cfg.CONF.signature_checking and \
            not security.verify_signature(measurements,
                                          cfg.CONF.driver_metering_secret):
            LOG.error('Bad message signature')
        else:
            try:
                """
                Measurement format:
                  * probe_id
                  * timestamp: time of the measure
                  * measure: data retrieved by probes
                  * data_type: type of measure (power, network...)
                  * params: additional informations
                """
                probe = measurements['probe_id'].encode('utf-8')
                timestamp = measurements['timestamp']
                measure = measurements['measure']
                params = measurements['data_type']
                data_type = params['name']
                probe_names = ast.literal_eval(measurements['probes_names'])
                for key in measurements.keys():
                    if not key in ['probe_id', 'timestamp', 'measure', 'data_type', 'message_signature']:
                        params[key] = measurements[key]
                function(probe, probe_names, data_type, timestamp, measure, params)
            except (TypeError, ValueError):
                raise
                LOG.error('Malformed data: %s' % measurements)
            except KeyError:
                LOG.error('Malformed message (missing required key)')

