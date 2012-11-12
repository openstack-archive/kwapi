#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import time
import socket
import os, os.path
import threading

class Record(dict):
    
    def __init__(self, timestamp, kwh, watts):
        dict.__init__(self)
        self._dict = {}
        self['timestamp'] = timestamp
        self['kwh'] = kwh
        self['w'] = watts
    
    def add(self, watts):
        currentTime = time.time()
        self['kwh'] += (currentTime - self['timestamp']) / 3600.0 * (watts / 1000.0)
        self['w'] = watts
        self['timestamp'] = currentTime

class Collector:
    
    def __init__(self):
        self.database = {}
    
    def add(self, probe, watts):
        if probe in self.database:
            self.database[probe].add(watts)
        else:
            record = Record(timestamp=time.time(), kwh=0.0, watts=watts)
            self.database[probe] = record
    
    def remove(self, probe):
        if probe in self.database:
            del self.database[probe]
            return True
        else:
            return False
    
    def clean(self, timeout, periodic):
        # Cleaning        
        for probe in self.database.keys():
            if time.time() - self.database[probe].timestamp > timeout:
                self.remove(probe)
        
        # Cancel next execution of this function
        try:
            self.timer.cancel()
        except AttributeError:
            pass
        
        # Schedule periodic execution of this function
        if periodic:
            self.timer = threading.Timer(timeout, self.clean, [timeout])
            self.timer.start()
    
    def listen(self, socket_name):
        if os.path.exists(socket_name):
            os.remove(socket_name)
         
        server = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        server.bind(socket_name)
         
        while True:
            datagram = server.recv(1024)
            if not datagram:
                print 'Error: not datagram'
                break
            else:
                data = datagram.split(':')
                if len(data) == 2:
                    try:
                        self.add(data[0], float(data[1]))
                    except:
                        logging.error('Datagram format error: %s' % datagram)
                else:
                    logging.error('Malformed datagram: %s' % datagram)
        server.close()
        os.remove(socket_name)
    
    def start_listen(self, socket_name):
        thread = threading.Thread(target=self.listen, args=[socket_name])
        thread.start()
