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
import threading
import time

from oslo.config import cfg
import zmq

from kwapi.openstack.common import log
from kwapi import security

LOG = log.getLogger(__name__)

collector_opts = [
    cfg.BoolOpt('signature_checking',
                required=True,
                ),
    cfg.IntOpt('cleaning_interval',
               required=True,
               ),
    cfg.MultiStrOpt('probes_endpoint',
                    required=True,
                    ),
    cfg.MultiStrOpt('watch_probe',
                    required=False,
                    ),
    cfg.StrOpt('driver_metering_secret',
               required=True,
               ),
]

cfg.CONF.register_opts(collector_opts)


class Record(dict):
    """Contains fields (timestamp, kwh, w) and a method to update
    consumption.

    """

    def __init__(self, timestamp, kwh, watts):
        """Initializes fields with the given arguments."""
        dict.__init__(self)
        self._dict = {}
        self['timestamp'] = timestamp
        self['kwh'] = kwh
        self['w'] = watts

    def add(self, watts):
        """Updates fields with consumption data."""
        currentTime = time.time()
        self['kwh'] += (currentTime - self['timestamp']) / 3600.0 * \
                       (watts / 1000.0)
        self['w'] = watts
        self['timestamp'] = currentTime


class Collector:
    """Collector gradually fills its database with received values from
    wattmeter drivers.

    """

    def __init__(self):
        """Initializes an empty database and start listening the endpoint."""
        LOG.info('Starting Collector')
        self.database = {}
        thread = threading.Thread(target=self.listen)
        thread.daemon = True
        thread.start()

    def add(self, probe, watts):
        """Creates (or updates) consumption data for this probe."""
        if probe in self.database.keys():
            self.database[probe].add(watts)
        else:
            record = Record(timestamp=time.time(), kwh=0.0, watts=watts)
            self.database[probe] = record

    def remove(self, probe):
        """Removes this probe from database."""
        if probe in self.database.keys():
            del self.database[probe]
            return True
        else:
            return False

    def clean(self):
        """Removes probes from database if they didn't send new values over
        the last period (seconds). If periodic, this method is executed
        automatically after the timeout interval.

        """
        LOG.info('Cleaning collector')
        # Cleaning
        for probe in self.database.keys():
            if time.time() - self.database[probe]['timestamp'] > \
                    cfg.CONF.cleaning_interval:
                LOG.info('Removing data of probe %s' % probe)
                self.remove(probe)

        # Schedule periodic execution of this function
        if cfg.CONF.cleaning_interval > 0:
            timer = threading.Timer(cfg.CONF.cleaning_interval, self.clean)
            timer.daemon = True
            timer.start()

    def listen(self):
        """Subscribes to ZeroMQ messages, and adds received measurements to the
        database. Messages are dictionaries dumped in JSON format.

        """
        LOG.info('Collector listenig to %s' % cfg.CONF.probes_endpoint)

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
                    not security.verify_signature(
                        measurements,
                        cfg.CONF.driver_metering_secret):
                LOG.error('Bad message signature')
            else:
                try:
                    self.add(measurements['probe_id'],
                             float(measurements['w']))
                except (TypeError, ValueError):
                    LOG.error('Malformed power consumption data: %s'
                              % measurements['w'])
                except KeyError:
                    LOG.error('Malformed message (missing required key)')
