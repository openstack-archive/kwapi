# -*- coding: utf-8 -*-

import logging
import os, os.path
import socket
import threading
import time

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
    
    def listen(self, socket_name):
        """Listen the socket, and add received values to the database.
        Datagram format is "probe:value".
        
        """
        logging.info('Collector listenig to %s' % socket_name)
        
        if os.path.exists(socket_name):
            os.remove(socket_name)
         
        server = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        server.bind(socket_name)
         
        while True:
            datagram = server.recv(1024)
            if not datagram:
                logging.error('Received data are not datagram')
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
