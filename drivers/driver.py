#!/usr/bin/env python
# -*- coding: utf-8 -*-

from threading import Thread

class Driver(Thread):
    
    def __init__(self, probe_ids, kwargs):
        Thread.__init__(self)
        self.probe_ids = probe_ids
        self.kwargs = kwargs
        self.probe_observers = []
        self.terminate = False
    
    def run(self):
         raise NotImplementedError
    
    def update_value(self, probe_id, value):
        for notify_new_value in self.probe_observers :
            notify_new_value(probe_id, value)
    
    def subscribe(self, observer):
        self.probe_observers.append(observer)
    
    def stop(self):
        self.terminate = True
