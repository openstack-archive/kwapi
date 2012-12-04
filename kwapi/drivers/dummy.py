# -*- coding: utf-8 -*-

from random import randrange
import time

from driver import Driver

class Dummy(Driver):
    """Dummy driver derived from Driver class. Usefull for tests."""
    
    def __init__(self, probe_ids, **kwargs):
        """Initializes the dummy driver.
        
        Keyword arguments:
        probe_ids -- list containing the probes IDs (a wattmeter monitor sometimes several probes
        kwargs -- keywords (min_value and max_value) defining the random value interval
        
        """
        Driver.__init__(self, probe_ids, kwargs)
        self.min_value = int(kwargs.get('min', 75))
        self.max_value = int(kwargs.get('max', 100))
    
    def run(self):
        """Starts the driver thread."""
        while not self.stop_request_pending():
            for probe_id in self.probe_ids:
                measurements = {}
                measurements['w'] = randrange(self.min_value, self.max_value)
                measurements['v'] = 230.0
                measurements['a'] = measurements['w'] / measurements['v']
                self.send_measurements(probe_id, measurements)
            time.sleep(1)
