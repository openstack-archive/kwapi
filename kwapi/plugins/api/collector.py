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

import threading
import time

from kwapi.utils import cfg, log

LOG = log.getLogger(__name__)

collector_opts = [
    cfg.BoolOpt('signature_checking',
                required=True,
                ),
    cfg.IntOpt('cleaning_interval',
               required=True,
               ),
    cfg.MultiStrOpt('probes_endpoint',
                    required=True,
                    ),
    cfg.MultiStrOpt('watch_probe',
                    required=False,
                    ),
    cfg.StrOpt('driver_metering_secret',
               required=True,
               ),
]

cfg.CONF.register_opts(collector_opts)


class Record(dict):
    """Contains fields (timestamp, value, unit) and a method to update
    consumption.

    """

    def __init__(self, timestamp, measure, data_type, params, integrated):
        """Initializes fields with the given arguments."""
        dict.__init__(self)
        self._dict = {}
        self['timestamp'] = timestamp
        self['type'] = params['type']
        self['unit'] = params['unit']
        if self['type'] != 'Gauge':
            # No integrated value
            self['value'] = measure
        else:
            self['integrated'] = integrated
            self['value'] = measure
        

    def add(self, timestamp, measure, params):
        """Updates fields with consumption data."""
        currentTime = timestamp 
        if self['type'] != 'Gauge':
            # No integrated value
            self['value'] = measure
        else:
            self['integrated'] += (currentTime - self['timestamp']) / 3600.0 * \
                           (measure / 1000.0)
            self['value'] = measure
        self['timestamp'] = currentTime


class Collector:
    """Collector gradually fills its database with received values from
    wattmeter drivers.

    """

    def __init__(self):
        """Initializes an empty database and start listening the endpoint."""
        LOG.info('Starting Collector')
        self.database = {}
        self.lock = threading.Lock()

    def add(self, probe, data_type, timestamp, measure, params):
        """Creates (or updates) consumption data for this probe."""
        self.lock.acquire()
        try:
            if data_type not in self.database.keys():
                self.database[data_type] = {}
            if probe in self.database[data_type].keys():
                self.database[data_type][probe].add(timestamp, measure, params)
            else:
                record = Record(timestamp=timestamp, measure=measure, \
                         data_type=data_type, params=params, integrated=0.0)
                self.database[data_type][probe] = record
        except:
            LOG.error("Fail to add %s datas" % probe)
        finally:
            self.lock.release()

    def remove(self, probe):
        """Removes this probe from database."""
        self.lock.acquire()
        try:
            for data_type in self.database.keys():
                if probe in self.database[data_type].keys():
                    del self.database[data_type][probe]
            return True
        except KeyError:
            return False
        finally:
            self.lock.release()

    def clean(self):
        """Removes probes from database if they didn't send new values over
        the last period (seconds). If periodic, this method is executed
        automatically after the timeout interval.

        """
        LOG.info('Cleaning collector')
        # Cleaning
        for data_type in self.database.keys():
            for probe in self.database[data_type].keys():
                if time.time() - self.database[data_type][probe]['timestamp'] > \
                            cfg.CONF.cleaning_interval:
                    LOG.info('Removing data of probe %s' % probe)
                    self.remove(probe)
        # Schedule periodic execution of this function
        if cfg.CONF.cleaning_interval > 0:
            timer = threading.Timer(cfg.CONF.cleaning_interval, self.clean)
            timer.daemon = True
            timer.start()
