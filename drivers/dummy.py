# -*- coding: utf-8 -*-

from driver import Driver
from random import randrange
import time

class Dummy(Driver):
    
    def __init__(self, probe_ids, **kwargs):
        Driver.__init__(self, probe_ids, kwargs)
        self.min_value = int(kwargs.get('min', 75))
        self.max_value = int(kwargs.get('max', 100))
    
    def run(self):
        while not self.terminate:
            for probe_id in self.probe_ids:
                value = randrange(self.min_value, self.max_value)
                self.update_value(probe_id, value)
            time.sleep(1)
