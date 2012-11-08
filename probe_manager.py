#!/usr/bin/env python
# -*- coding: utf-8 -*-

from configobj import ConfigObj, Section, flatten_errors
from validate import Validator, ValidateError
import drivers
import sys

from subprocess import call
import os
import socket
import thread
import threading
import signal

threads = []
socket_name = '/tmp/kwapi-collector'

def driver_check(class_name):
    try:
        getattr(sys.modules['drivers'], class_name)
    except AttributeError:
        raise ValidateError("%s doesn't exist." % class_name)
    return class_name

def validate(config_file, configspec_file):
    config = ConfigObj(config_file, configspec=configspec_file)
    validator = Validator({'driver': driver_check})
    results = config.validate(validator)
    if results != True:
        for(section_list, key, _) in flatten_errors(config, results):
            if key is not None:
                print 'The "%s" key in the section "%s" failed validation.' % (key, ', '.join(section_list))
            else:
                print 'The following section was missing:%s.' % ', '.join(section_list)
        return False
    else:
        return config

def load_probes_from_conf(config):
    for key in config.keys():
        if isinstance(config[key], Section):
            class_name = config[key]['driver']
            probe_ids = config[key]['probes']
            kwargs = {}
            if 'parameters' in config[key].keys():
                kwargs = config[key]['parameters']
            thread = load_probe(class_name, probe_ids, kwargs)
            threads.append(thread)

def load_probe(class_name, probe_ids, kwargs):
    try:
        probeClass = getattr(sys.modules['drivers'], class_name)
    except AttributeError:
        raise NameError("%s doesn't exist." % class_name)
    try:
        probeObject = probeClass(probe_ids, **kwargs)
    except Exception as exception:
        print 'Probe', probe_ids, 'error: %s' % exception
        return
    probeObject.subscribe(send_value)
    probeObject.start()
    return probeObject

def check_probes_alive(interval=60):
    # TODO : default value because main exit before this thread...
    print 'Check probes every', interval, 'seconds'
    for index, thread in enumerate(threads):
        if not thread.is_alive():
            print thread, ' crashed!'
            threads[index] = load_probe(thread.__class__.__name__, thread.probe_ids, thread.kwargs)
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
    if os.path.exists(socket_name):
        client = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        client.connect(socket_name)
        client.send(probe_id + ':' + str(value))
        client.close()

if __name__ == "__main__":
    config = validate('kwapi.conf', 'configspec.ini')
    if not config:
        sys.exit(1)
    
    load_probes_from_conf(config)
    
    # Check probe crashes
    check_probes_alive(4)
    
    signal.signal(signal.SIGTERM, signal_handler)
    try:
        signal.pause()
    except KeyboardInterrupt:
        terminate()
