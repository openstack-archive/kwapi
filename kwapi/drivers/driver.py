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
from threading import Thread, Event

from kwapi.utils import cfg
import zmq

from kwapi.utils import log
from kwapi import security

LOG = log.getLogger(__name__)

driver_opts = [
    cfg.BoolOpt('enable_signing',
                required=True,
                ),
    cfg.StrOpt('metering_secret',
               required=True,
               ),
]

cfg.CONF.register_opts(driver_opts)


class Driver(Thread):
    """Generic driver class, derived from Thread."""

    def __init__(self, probe_ids, probe_data_type, kwargs):
        """Initializes driver."""
        LOG.info('Loading driver %s(probe_ids=%s, kwargs=%s)'
                 % (self.__class__.__name__, probe_ids, kwargs))
        Thread.__init__(self)
        self.probe_ids = probe_ids
        self.probe_data_type = probe_data_type
        self.kwargs = kwargs
        self.probe_observers = []
        self.stop_request = Event()
        self.publisher = zmq.Context.instance().socket(zmq.PUB)
        self.publisher.connect('inproc://drivers')

    def run(self):
        """
        Runs the driver thread. 
        Needs to be implemented in a derived class.

        """
        raise NotImplementedError

    def join(self):
        """Asks the driver thread to terminate."""
        self.stop_request.set()
        super(Driver, self).join()
        LOG.info('Unloading driver %s(probe_ids=%s, kwargs=%s)'
                 % (self.__class__.__name__, self.probe_ids, self.kwargs))

    def stop_request_pending(self):
        """Returns true if a stop request is pending."""
        return self.stop_request.is_set()

    def send_measurements(self, probe_id, measurements):
        """Sends a message via ZeroMQ (dictionary dumped in JSON format)."""
        measurements['probe_id'] = probe_id
        if cfg.CONF.enable_signing:
            security.append_signature(measurements, cfg.CONF.metering_secret)
        self.publisher.send_multipart(
            [
                probe_id + '.',
                json.dumps(measurements)
            ]
        )

    def create_measurements(self, probe_id, time, metrics):
        """Return the measure with specific fields associated"""
	measurements = {}
	# Add default fields
	measurements['probe_id'] = probe_id
	measurements['timestamp'] = time
        measurements['measure'] = metrics
        measurements['data_type'] = self.probe_data_type
	return measurements

    def subscribe(self, observer):
        """Appends the observer (callback method) to the observers list."""
        self.probe_observers.append(observer)

    def stop(self):
        """Asks the probe to terminate."""
        self.terminate = True

