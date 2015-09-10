# -*- coding: utf-8 -*-
#
# Author: Clement Parisot <clement.parisot@inria.fr>
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

import os
import errno
import socket

import numpy as np

from kwapi.utils import cfg, log
from threading import Lock, Timer
from datetime import datetime
from dateutil.relativedelta import relativedelta

from Queue import Queue
from tables import *
from pandas import HDFStore

import networkx as nx

LOG = log.getLogger(__name__)

hdf5_opts = [
    cfg.BoolOpt('signature_checking',
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
    cfg.StrOpt('hdf5_dir',
               required=True,
               ),
    cfg.StrOpt('start_date',
               required=True,
               ),
    cfg.IntOpt('split_days',
               required=True,
               ),
    cfg.IntOpt('split_weeks',
               required=True,
               ),
    cfg.IntOpt('split_months',
               required=True,
               ),
    cfg.IntOpt('chunk_size',
               required=True,
               ),
]

cfg.CONF.register_opts(hdf5_opts)
hostname = socket.getfqdn().split('.')
site = hostname[1] if len(hostname) >= 2 else hostname[0]
# probe list
probes_sets = {}
# Mapping between name and probes
probes_names_maps = {}
# One queue per metric
buffered_values = {
    "power": Queue(),
    "network_in" : Queue(),
    "network_out": Queue(),
}

def update_hdf5(probe, probes_names, data_type, timestamp, metrics, params):
    """Updates HDF5 file associated with this probe."""
    if not data_type in buffered_values:
        return
    if not type(probes_names) == list:
        probes_names = list(probes_names)
    for probe_name in probes_names:
        if data_type in probes_names_maps:
            probes_names_maps[data_type].add_edge(probe_name,probe)
        else:
            probes_names_maps[data_type] = nx.Graph()
            probes_names_maps[data_type].add_edge(probe_name,probe)
    if probes_sets.get(data_type, None):
        probes_sets[data_type].add(probe)
    else:
        probes_sets[data_type] = set([probe])

def get_probe_path(probe):
    site = probe.split(".")[0]
    host = ".".join(probe.split(".")[1:])
    return "/%s/%s" % (site, host.replace('.', "__").replace('-', '_'))


class ProbeMeasures(IsDescription):
    timestamp = Float64Col()
    measure = Int64Col()

class HDF5_Collector:
    """
    HDF5 Collector gradually fills HDF5 files with received values from
    drivers.
    """

    def __init__(self, data_type):
        """Initializes an empty database and start listening the endpoint."""
        LOG.info('Starting Writter')
        self.data_type = data_type
        self.lock = Lock()
        self.measurements = dict()
        self.chunk_size = cfg.CONF.chunk_size
        """Creates all required directories."""
        try:
            os.makedirs(cfg.CONF.hdf5_dir)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

        """Retrieve next update date"""
        self.start_date = datetime.strptime(cfg.CONF.start_date, "%Y/%m/%d")
        self.save_date = self.start_date
        self.delta = relativedelta(days = cfg.CONF.split_days, weeks = cfg.CONF.split_weeks,
                            months = cfg.CONF.split_months)
        self.next_save_date = self.save_date + self.delta
        today = datetime.now()
        while self.next_save_date < today:
            self.save_date = self.next_save_date
            self.next_save_date += self.delta
        LOG.info("Current save date: %s" % self.save_date)
        LOG.info("Next save date:    %s" % self.next_save_date)
        self.database = self.get_hdf5_file()
        store = openFile(self.database, mode="a", title = "Fine grained measures")
        store.close()

    def get_hdf5_file(self):
        if self.next_save_date <= datetime.now():
            self.save_date = self.next_save_date
            self.next_save_date += self.delta
            LOG.info("Rotate to new file %s" % self.save_date.strftime("%Y_%m_%d"))
        return cfg.CONF.hdf5_dir + \
            '/%s_%s_%s' % (self.save_date.strftime("%Y_%m_%d"), self.data_type, 'store.h5')



    def write_datas(self):
        """Stores data for this probe."""
        """Updates HDF5 file associated with this probe."""
        if not self.data_type in buffered_values:
            return
        for probe, timestamp, metrics in iter(buffered_values[self.data_type].get, 'STOP'):
            if not probe in self.measurements:
                self.measurements[probe] = []
            self.measurements[probe].append((timestamp, metrics))
            if len(self.measurements[probe]) >= self.chunk_size:
                zipped = map(list, zip(*self.measurements[probe]))
                self.write_hdf5(probe,
                                np.array(zipped[0]),  # Timestp
                                np.array(zipped[1]))  # measures
                del self.measurements[probe][:]
            buffered_values[self.data_type].task_done()
        # Flush datas
        LOG.info("FLUSH DATAS... %s", self.data_type)
        keys = self.measurements.keys()
        for probe in keys:
            zipped = map(list, zip(*self.measurements[probe]))
            self.write_hdf5(probe,
                            np.array(zipped[0]),  # Timestp
                            np.array(zipped[1]))  # measures
            del self.measurements[probe]
        buffered_values[self.data_type].task_done()


    def write_hdf5(self, probe, timestamps, measures):
        self.lock.acquire()
        f = openFile(self.get_hdf5_file(), mode = "a")
        try:
            path = get_probe_path(probe)
            _, cluster, probe_name = path.split('/')
            if not cluster in f.root:
                group = f.createGroup("/", cluster, "cluster")
            group = f.getNode("/"+cluster)
            if not path in f:
                table = f.createTable(group, probe_name, ProbeMeasures, "probe")
            table = f.getNode(path)
            for x in range(len(timestamps)):
                table.row['timestamp'] = timestamps[x]
                table.row['measure'] = measures[x]
                table.row.append()
            table.flush()
            probes_neighbors = probes_names_maps[self.data_type].neighbors(probe)
            for probe_neighbor in probes_neighbors:
                neighbor_path = get_probe_path(probe_neighbor)
                if not neighbor_path in f:
                    _, cluster,neighbor_probe_name = neighbor_path.split('/')
                    f.create_hard_link(group, neighbor_probe_name, table)
        except Exception as e:
            LOG.error("Fail to add %s datas" % probe)
            LOG.error("%s" % e)
        finally:
            f.flush()
            f.close()
            self.lock.release()

    #OK
    def get_probes_list(self):
        probes = []
        for probe in list(probes_sets[self.data_type]):
            try:
                site, host, port = probe.split(".")
                probes.append("%s.%s.%s.grid5000.fr" % (port, host, site))
                probes = sorted(probes, key = lambda x: "%s" % x.split(".")[1])
            except:
                LOG.error("Can't parse %s" % probe)
        return probes

    def get_probes_names(self):
        probes_names = set()
        for probe_id in list(probes_sets[self.data_type]):
            for probe in probes_names_maps[self.data_type].neighbors(probe_id):
                try:
                    probes_names.add(probe)
                except:
                    LOG.error("Can't parse %s" % probe)
                    continue
        return list(probes_names)

    def get_hdf5_files(self, start_time, end_time):
        list_files = []
        if end_time < start_time:
            return list_files
        else:
            try:
                file_date = datetime.fromtimestamp(float(start_time))
                end_date  = datetime.fromtimestamp(float(end_time))
                if file_date < self.start_date:
                    file_date = self.start_date
                if end_date > datetime.now():
                    end_date = datetime.now()
                start_date = self.start_date
                while start_date < file_date:
                    start_date += self.delta
                file_date = start_date - self.delta
                while file_date < end_date:
                    s = cfg.CONF.hdf5_dir + '/%s_%s_%s' % (file_date.strftime("%Y_%m_%d"), self.data_type, 'store.h5')
                    if os.path.isfile(s):
                        list_files.append(s)
                    file_date += self.delta
                return list_files
            except Exception as e:
                LOG.error("Get file list: %s" % e)
                return []

    def select_probes_datas(self, probes, start_time, end_time):
        message = dict()
        self.lock.acquire()
        list_files = self.get_hdf5_files(start_time, end_time)
        try:
            for filename in list_files:
                for probe in probes:
                    if not probe in message:
                        # Init message for probe
                        message[probe] = dict()
                        message[probe]["uid"] = ".".join(probe.split('.')[1:])
                        message[probe]["to"] =  int(end_time)
                        message[probe]["from"] = int(start_time)
                        message[probe]['values'] = []
                        message[probe]['timestamps'] = []
                    path = get_probe_path(probe)
                    if path:
                        f = openFile(filename, mode = "r")
                        try:
                            ts = []
                            table = f.getNode(path)
                            ts = [(x["timestamp"], x["measure"]) \
                                  for x in table.where("(timestamp >= %s) & (timestamp <= %s)" \
                                                       % (start_time, end_time))]
                            timestamps, values = zip(*ts)
                            message[probe]['values'] += list(values)
                            message[probe]['timestamps'] += list(timestamps)
                        except Exception as e:
                            LOG.error("%s" % e)
                        finally:
                            f.close()
        except Exception as e:
            LOG.error("%s" % e)
        finally:
            self.lock.release()
        return message
