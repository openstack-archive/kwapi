#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import socket
import sys
import signal
from subprocess import call
import thread
import threading
from configobj import Section
import config
import drivers

threads = []

def setup_logging(log_level, file_name, print_to_stdout):
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', filename=file_name, filemode='w', level=log_level)
    if print_to_stdout:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        logger = logging.getLogger()
        logger.addHandler(console_handler)

def load_probes_from_conf(config):
    for key in config.keys():
        if isinstance(config[key], Section):
            class_name = config[key]['driver']
            probe_ids = config[key]['probes']
            kwargs = {}
            if 'parameters' in config[key].keys():
                kwargs = config[key]['parameters']
            thread = load_probe(class_name, probe_ids, kwargs)
            if thread is not None:
                threads.append(thread)

def load_probe(class_name, probe_ids, kwargs):
    try:
        probeClass = getattr(sys.modules['drivers'], class_name)
    except AttributeError:
        raise NameError("%s doesn't exist." % class_name)
    try:
        probeObject = probeClass(probe_ids, **kwargs)
    except Exception as exception:
        logging.error('Probe %s constructor error: %s' % (probe_ids, exception))
        return None
    probeObject.subscribe(send_value)
    probeObject.start()
    return probeObject

def check_probes_alive(interval):
    for index, thread in enumerate(threads):
        if not thread.is_alive():
            logging.warning('%s crashed!', thread)
            threads[index] = load_probe(thread.__class__.__name__, thread.probe_ids, thread.kwargs)
    if interval > 0:
        timer = threading.Timer(interval, check_probes_alive, [interval])
        timer.daemon = True
        timer.start()

def signal_handler(signum, frame):
    if signum is signal.SIGTERM:
        terminate()

def terminate():
    for thread in threads:
        thread.stop()
    for thread in threads:
        thread.join()

def send_value(probe_id, value):
    # TODO Do not read config everytime
    socket_name = config.get_config('kwapi.conf', 'configspec.ini')['socket']
    if os.path.exists(socket_name):
        client = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        client.connect(socket_name)
        client.send(probe_id + ':' + str(value))
        client.close()

if __name__ == "__main__":
    setup_logging(logging.DEBUG, 'kwapi.log', print_to_stdout=True)
    
    config = config.get_config('kwapi.conf', 'configspec.ini')
    if config is None:
        sys.exit(1)
    
    load_probes_from_conf(config)
    
    # Check probe crashes
    check_probes_alive(config['check_probes_interval'])
    
    signal.signal(signal.SIGTERM, signal_handler)
    try:
        signal.pause()
    except KeyboardInterrupt:
        terminate()
