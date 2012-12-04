# -*- coding: utf-8 -*-

import json
import threading
import time

import zmq

from kwapi.openstack.common import cfg, log

LOG = log.getLogger(__name__)

collector_opts = [
    cfg.StrOpt('probes_endpoint',
               required=True,
               ),
    cfg.IntOpt('cleaning_interval',
           required=True,
           ),
    ]

cfg.CONF.register_opts(collector_opts)

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
    
    def __init__(self, conf):
        """Initializes an empty database and start listening the endpoint."""
        LOG.info('Starting Collector')
        self.database = {}
        thread = threading.Thread(target=self.listen, args=[conf])
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
    
    def clean(self, conf, periodic):
        """Removes probes from database if they didn't send new values over the last period (seconds).
        If periodic, this method is executed automatically after the timeout interval.
        
        """
        LOG.info('Cleaning collector')
        # Cleaning        
        for probe in self.database.keys():
            if time.time() - self.database[probe]['timestamp'] > conf.cleaning_interval:
                LOG.info('Removing data of probe %s' % probe)
                self.remove(probe)
        
        # Cancel next execution of this function
        try:
            self.timer.cancel()
        except AttributeError:
            pass
        
        # Schedule periodic execution of this function
        if periodic:
            self.timer = threading.Timer(conf.cleaning_interval, self.clean, [conf, True])
            self.timer.daemon = True
            self.timer.start()
    
    def listen(self, conf):
        """Subscribes to ZeroMQ messages, and adds received measurements to the database.
        Messages are dictionaries dumped in JSON format.
        
        """
        LOG.info('Collector listenig to %s' % conf.probes_endpoint)
        
        context = zmq.Context()
        subscriber = context.socket(zmq.SUB)
        subscriber.setsockopt(zmq.SUBSCRIBE, '')
        subscriber.connect(conf.probes_endpoint)
        
        while True:
            message = subscriber.recv()
            measurements = json.loads(message)
            if not isinstance(measurements, dict):
                LOG.error('Bad message type (not a dict)')
            else:
                try:
                    self.add(measurements['probe_id'], float(measurements['w']))
                except KeyError:
                    LOG.error('Malformed message (missing required key)')
