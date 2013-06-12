# -*- coding: utf-8 -*-
#
# Author: François Rossigneux <francois.rossigneux@inria.fr>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Loads and checks driver threads."""

import ast
import signal
import thread
from threading import Lock, Timer

from oslo.config import cfg
import zmq

from kwapi.openstack.common import log

LOG = log.getLogger(__name__)

driver_manager_opts = [
    cfg.IntOpt('check_drivers_interval',
               required=True,
               ),
    cfg.StrOpt('probes_endpoint',
               required=True,
               ),
]

cfg.CONF.register_opts(driver_manager_opts)

threads = []
lock = Lock()


def load_all_drivers():
    """Loads all drivers from config file."""
    parser = cfg.ConfigParser(cfg.CONF.config_file[0], {})
    parser.parse()
    for section, entries in parser.sections.iteritems():
        if section != 'DEFAULT':
            class_name = entries['driver'][0]
            probe_ids = ast.literal_eval(entries['probes'][0])
            kwargs = {}
            if 'parameters' in entries.keys():
                kwargs = ast.literal_eval(entries['parameters'][0])
            lock.acquire()
            driver_thread = load_driver(class_name, probe_ids, kwargs)
            if driver_thread is not None:
                threads.append(driver_thread)
            lock.release()


def load_driver(class_name, probe_ids, kwargs):
    """Starts a probe thread."""
    try:
        module = __import__('kwapi.drivers.' + class_name.lower(),
                            fromlist=class_name)
        probe_class = getattr(module, class_name)
    except ImportError:
        raise NameError("%s doesn't exist." % class_name)
    try:
        probe_object = probe_class(probe_ids, **kwargs)
    except Exception as exception:
        LOG.error('Exception occurred while initializing %s(%s, %s): %s'
                  % (class_name, probe_ids, kwargs, exception))
    else:
        probe_object.start()
        return probe_object


def check_drivers_alive():
    """Checks all drivers and reloads those that crashed.
    This method is executed automatically at the given interval.

    """
    if lock.acquire(False):
        LOG.info('Checks driver threads')
        for index, driver_thread in enumerate(threads):
            if not driver_thread.is_alive():
                LOG.warning('%s(probe_ids=%s, kwargs=%s) is crashed'
                            % (driver_thread.__class__.__name__,
                            driver_thread.probe_ids, driver_thread.kwargs))
                new_thread = load_driver(driver_thread.__class__.__name__,
                                         driver_thread.probe_ids,
                                         driver_thread.kwargs
                                         )
                if new_thread is not None:
                    threads[index] = new_thread
        # Schedule periodic execution of this function
        if cfg.CONF.check_drivers_interval > 0:
            timer = Timer(cfg.CONF.check_drivers_interval,
                          check_drivers_alive)
            timer.daemon = True
            timer.start()
        lock.release()


def start_zmq_server():
    """Forwards probe values to the probes_endpoint."""
    context = zmq.Context.instance()
    context.set(zmq.MAX_SOCKETS, 100000)
    frontend = context.socket(zmq.SUB)
    frontend.bind('inproc://drivers')
    frontend.setsockopt(zmq.SUBSCRIBE, '')
    backend = context.socket(zmq.PUB)
    backend.bind(cfg.CONF.probes_endpoint)
    thread.start_new_thread(zmq.device, (zmq.FORWARDER, frontend, backend))


def signal_handler(signum, frame):
    """Intercepts TERM signal and properly terminates probe threads."""
    if signum is signal.SIGTERM:
        terminate()


def terminate():
    """Terminates driver threads."""
    lock.acquire()
    for driver in threads:
        thread.start_new_thread(driver.join, ())
