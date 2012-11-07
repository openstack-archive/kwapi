# -*- coding: utf-8 -*-

from driver import Driver
from random import randrange
import time

class Dummy(Driver):
    
    def __init__(self, probe_id, **kwargs):
        Driver.__init__(self, probe_id)
        self.min_value = int(kwargs.get('min_value', 75))
        self.max_value = int(kwargs.get('max_value', 100))
    
    def run(self):
        while not self.terminate:
            value = randrange(self.min_value, self.max_value)
            self.update_value(value)
            time.sleep(1)
