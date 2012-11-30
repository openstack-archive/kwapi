# -*- coding: utf-8 -*-

from threading import Thread, Event

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
    
    def update_value(self, probe_id, value):
        """Calls the callback method of all observers, with the following arguments: probe_id, value."""
        for notify_new_value in self.probe_observers :
            notify_new_value(probe_id, value)
    
    def subscribe(self, observer):
        """Appends the observer (callback method) to the observers list."""
        self.probe_observers.append(observer)
    
    def stop(self):
        """Asks the probe to terminate."""
        self.terminate = True
