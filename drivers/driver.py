#!/usr/bin/env python
# -*- coding: utf-8 -*-

from threading import Thread

class Driver(Thread):
    
    def __init__(self, probe_id):
        Thread.__init__(self)
        self.name = probe_id
        self.probe_observers = []
        self.terminate = False
    
    def run(self):
         raise NotImplementedError
    
    def update_value(self, value):
        for notify_new_value in self.probe_observers :
            notify_new_value(self.name, value)
    
    def subscribe(self, observer):
        self.probe_observers.append(observer)
    
    def stop(self):
        self.terminate = True
