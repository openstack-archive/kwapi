# -*- coding: utf-8 -*-

"""Loads and checks driver threads."""

import ast
import sys
import signal
import thread
from threading import Timer

import zmq

from kwapi.openstack.common import cfg, log

LOG = log.getLogger(__name__)

driver_manager_opts = [
    cfg.StrOpt('probes_endpoint',
               required=True,
               ),
    cfg.IntOpt('check_drivers_interval',
               required=True,
               ),
    ]

cfg.CONF.register_opts(driver_manager_opts)

threads = []

def load_all_drivers(conf):
    """Loads all drivers from config."""
    parser = cfg.ConfigParser(cfg.CONF.config_file[0], {})
    parser.parse()
    for section, entries in parser.sections.iteritems():
        if section != 'DEFAULT':
            class_name = entries['driver'][0]
            probe_ids = ast.literal_eval(entries['probes'][0])
            kwargs = {}
            if 'parameters' in entries.keys():
                kwargs = ast.literal_eval(entries['parameters'][0])
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
        LOG.error('Exception occurred while initializing %s(%s, %s): %s' % (class_name, probe_ids, kwargs, exception))
    else:
        probeObject.start()
        return probeObject

def check_drivers_alive(conf):
    """Checks all drivers and reloads those that crashed.
    This method is executed automatically at the given interval.
    
    """
    LOG.info('Checks driver threads')
    for index, thread in enumerate(threads):
        if not thread.is_alive():
            LOG.warning('%s(probe_ids=%s, kwargs=%s) is crashed' % (thread.__class__.__name__, thread.probe_ids, thread.kwargs))
            new_thread = load_driver(thread.__class__.__name__, thread.probe_ids, thread.kwargs)
            if new_thread is not None:
                threads[index] = new_thread
    if conf.check_drivers_interval > 0:
        timer = Timer(conf.check_drivers_interval, check_drivers_alive, [conf])
        timer.daemon = True
        timer.start()

def start_zmq_server(conf):
    """Forwards probe values to the probes_endpoint defined in conf."""
    context = zmq.Context.instance()
    frontend = context.socket(zmq.SUB)
    frontend.bind('inproc://drivers')
    frontend.setsockopt(zmq.SUBSCRIBE, '')
    backend = context.socket(zmq.PUB)
    backend.bind(conf.probes_endpoint)
    thread.start_new_thread(zmq.device, (zmq.FORWARDER, frontend, backend))

def signal_handler(signum, frame):
    """Intercepts TERM signal and properly terminates probe threads."""
    if signum is signal.SIGTERM:
        terminate()

def terminate():
    """Terminates driver threads."""
    for driver in threads:
        thread.start_new_thread(driver.join, ())
