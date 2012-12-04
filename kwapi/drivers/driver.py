# -*- coding: utf-8 -*-

import json
from threading import Thread, Event

import zmq

from kwapi.openstack.common import log

LOG = log.getLogger(__name__)

class Driver(Thread):
    """Generic driver class, derived from Thread."""
    
    def __init__(self, probe_ids, kwargs):
        """Initializes driver."""
        LOG.info('Loading driver %s(probe_ids=%s, kwargs=%s)' % (self.__class__.__name__, probe_ids, kwargs))
        Thread.__init__(self)
        self.probe_ids = probe_ids
        self.kwargs = kwargs
        self.probe_observers = []
        self.stop_request = Event()
        self.publisher = zmq.Context.instance().socket(zmq.PUB)
        self.publisher.connect('inproc://drivers')
    
    def run(self):
        """Run the driver thread. Needs to be implemented in a derived class."""
        raise NotImplementedError
    
    def join(self):
        """Asks the driver thread to terminate."""
        self.stop_request.set()
        super(Driver, self).join()
    
    def stop_request_pending(self):
        """Returns true if a stop request is pending."""
        return self.stop_request.is_set()
    
    def send_measurements(self, probe_id, measurements):
        """Sends a message via ZeroMQ (dictionary dumped in JSON format)."""
        measurements['probe_id'] = probe_id
        self.publisher.send(json.dumps(measurements))
    
    def subscribe(self, observer):
        """Appends the observer (callback method) to the observers list."""
        self.probe_observers.append(observer)
    
    def stop(self):
        """Asks the probe to terminate."""
        self.terminate = True
