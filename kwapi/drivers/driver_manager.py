# -*- coding: utf-8 -*-

"""Loads probe threads, and transmits their values via ZeroMQ."""

import logging
import os
import socket
import sys
import signal
from subprocess import call
import thread
from threading import Timer

from configobj import Section
import zmq

from kwapi import config

context = zmq.Context()
publisher = context.socket(zmq.PUB)
publisher.bind(config.CONF['probes_endpoint'])

threads = []

def load_all_drivers():
    """Loads all drivers from config."""
    for entry in config.CONF.values():
        if isinstance(entry, Section):
            class_name = entry['driver']
            probe_ids = entry['probes']
            kwargs = {}
            if 'parameters' in entry.keys():
                kwargs = entry['parameters']
            thread = load_driver(class_name, probe_ids, kwargs)
            if thread is not None:
                threads.append(thread)

def load_driver(class_name, probe_ids, kwargs):
    """Starts a probe thread."""
    try:
        probeClass = getattr(sys.modules['kwapi.drivers'], class_name)
    except AttributeError:
        raise NameError("%s doesn't exist." % class_name)
    try:
        probeObject = probeClass(probe_ids, **kwargs)
    except Exception as exception:
        logging.error('Exception occurred while initializing %s(%s, %s): %s' % (class_name, probe_ids, kwargs, exception))
    else:
        probeObject.subscribe(send_value)
        probeObject.start()
        return probeObject

def check_drivers_alive(interval):
    """Checks all drivers and reloads those that crashed.
    This method is executed automatically at the given interval.
    
    """
    logging.info('Checks driver threads')
    for index, thread in enumerate(threads):
        if not thread.is_alive():
            logging.warning('%s(probe_ids=%s, kwargs=%s) is crashed' % (thread.__class__.__name__, thread.probe_ids, thread.kwargs))
            new_thread = load_driver(thread.__class__.__name__, thread.probe_ids, thread.kwargs)
            if new_thread is not None:
                threads[index] = new_thread
    if interval > 0:
        timer = Timer(interval, check_drivers_alive, [interval])
        timer.daemon = True
        timer.start()

def signal_handler(signum, frame):
    """Intercepts TERM signal and properly terminates probe threads."""
    if signum is signal.SIGTERM:
        terminate()

def terminate():
    """Terminates driver threads"""
    for thread in threads:
        thread.join()
    publisher.close()

def send_value(probe_id, value):
    """Sends a message via ZeroMQ, with the following format: "probe_id:value"."""
    publisher.send(probe_id + ':' + str(value))
