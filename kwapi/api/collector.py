# -*- coding: utf-8 -*-

import logging
import os, os.path
import socket
import threading
import time

import zmq

class Record(dict):
    """Contains fields (timestamp, kwh, w) and a method to update consumption."""
    
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
        self['kwh'] += (currentTime - self['timestamp']) / 3600.0 * (watts / 1000.0)
        self['w'] = watts
        self['timestamp'] = currentTime

class Collector:
    """Collector gradually fills its database with received values from wattmeter drivers."""
    
    def __init__(self, socket_name):
        """Initializes an empty database and start listening the socket."""
        logging.info('Starting Collector')
        self.database = {}
        thread = threading.Thread(target=self.listen, args=[socket_name])
        thread.daemon = True
        thread.start()
    
    def add(self, probe, watts):
        """Creates (or update) consumption data for this probe."""
        if probe in self.database:
            self.database[probe].add(watts)
        else:
            record = Record(timestamp=time.time(), kwh=0.0, watts=watts)
            self.database[probe] = record
    
    def remove(self, probe):
        """Removes this probe from database."""
        if probe in self.database:
            del self.database[probe]
            return True
        else:
            return False
    
    def clean(self, timeout, periodic):
        """Removes probes from database if they didn't send new values over the last timeout period (seconds).
        If periodic, this method is executed automatically after the timeout interval.
        
        """
        logging.info('Cleaning collector')
        # Cleaning        
        for probe in self.database.keys():
            if time.time() - self.database[probe]['timestamp'] > timeout:
                logging.info('Removing data of probe %s' % probe)
                self.remove(probe)
        
        # Cancel next execution of this function
        try:
            self.timer.cancel()
        except AttributeError:
            pass
        
        # Schedule periodic execution of this function
        if periodic:
            self.timer = threading.Timer(timeout, self.clean, [timeout, True])
            self.timer.daemon = True
            self.timer.start()
    
    def listen(self, endpoint):
        """Subscribes to ZeroMQ messages, and adds received values to the database.
        Message format is "probe:value".
        
        """
        logging.info('Collector listenig to %s' % endpoint)
        
        context = zmq.Context()
        subscriber = context.socket(zmq.SUB)
        subscriber.setsockopt(zmq.SUBSCRIBE, '')
        subscriber.connect(endpoint)
        
        while True:
            message = subscriber.recv()
            data = message.split(':')
            if len(data) == 2:
                try:
                    self.add(data[0], float(data[1]))
                except:
                    logging.error('Message format error: %s' % message)
            else:
                logging.error('Malformed message: %s' % message)
