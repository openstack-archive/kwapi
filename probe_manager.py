#!/usr/bin/env python
# -*- coding: utf-8 -*-

from lxml import etree
from subprocess import call
import drivers
import sys
import os
import socket
import thread
import threading
import signal

threads = {}
socket_name = ''

def get_root(schema, xml):
    # Validating XML schema
    xsd = etree.parse(schema)
    schema = etree.XMLSchema(xsd)
    parser = etree.XMLParser(schema = schema)
    try:
        tree = etree.parse(xml, parser)
    except etree.XMLSyntaxError:
        return None
    return tree.getroot()

def send_value(probe_id, value):
    if os.path.exists(socket_name):
        client = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        client.connect(socket_name)
        client.send(probe_id + ':' + str(value))
        client.close()

def signal_handler(signum, frame):
    if signum is signal.SIGTERM:
        terminate()

def check_probes_alive(interval=60):
    # TODO : default value because main exit before this thread...
    print 'Check probes every', interval, 'seconds'
    for thread in threads.keys():
        if not threads[thread].is_alive():
            print threads[thread], ' crashed!'
            load_probe_from_xml(thread)
    timer = threading.Timer(interval, check_probes_alive, [interval])
    timer.daemon = True
    timer.start()

def terminate():
    check_probes_alive()
    for thread in threads.values():
        thread.stop()
    for thread in threads.values():
        thread.join()

def load_probe(class_name, probe_id, kwargs):
    try:
        probeClass = getattr(sys.modules['drivers'], class_name)
    except AttributeError:
        raise NameError("%s doesn't exist." % class_name)
    try:
        probeObject = probeClass(probe_id, **kwargs)
    except Exception as exception:
        print 'Probe "' + probe_id + '" error: %s' % exception
        return
    probeObject.subscribe(send_value)
    probeObject.start()
    threads[probe_id] = probeObject

def load_probe_from_xml(probe_id):
    print 'load_probe ', probe_id
    
    root = get_root('config.xsd', 'config.xml')
    if root is None:
        print "Configuration file isn't valid!"
        sys.exit(1)
    
    probe = root.find("./driver/probe[@id='%s']" % probe_id)
    class_name = probe.getparent().attrib['class']
    kwargs = {}
    for argument in probe:
        kwargs[argument.attrib['name']] = argument.attrib['value']
    load_probe(class_name, probe_id, kwargs)

if __name__ == "__main__":
    # Load and validate XML
    root = get_root('config.xsd', 'config.xml')
    if root is None:
        print "Configuration file isn't valid!"
        sys.exit(1)
    
    # Get socket path
    socket_name = root.find('collector').attrib['socket']
    
    # Load probes
    probe_ids = root.findall("./driver/probe")
    for probe_id in probe_ids:
        load_probe_from_xml(probe_id.attrib['id'])
    
    # Load probes
#    for driver in root.findall('driver'):
#        for probe in driver.findall('probe'):
#            class_name = driver.attrib['class']
#            probe_id = probe.attrib['id']
#            kwargs = {}
#            for argument in probe.findall('arg'):
#                kwargs[argument.attrib['name']] = argument.attrib['value']
#            thread.start_new_thread(load_probe, (class_name, probe_id, kwargs))
    
    # Check probe crashes
    check_probes_alive(60)
    
    signal.signal(signal.SIGTERM, signal_handler)
    try:
        signal.pause()
    except KeyboardInterrupt:
        terminate()
