import os
import errno
import socket
from pandas import HDFStore, TimeSeries, get_store, to_datetime, read_hdf
import numpy as np
from kwapi.utils import cfg, log
from datetime import date
from threading import Lock, Timer

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
]

cfg.CONF.register_opts(hdf5_opts)
hostname = socket.getfqdn().split('.')
site = hostname[1] if len(hostname) >= 2 else hostname[0]


def get_probe_path(probe):
    host = probe.split(".")[1]
    return "/%s/%s" % (site, host.replace('_', "__").replace('-', '_'))


class HDF5_Collector:
    """
    HDF5 Collector gradually fills HDF5 files with received values from
    drivers.
    """

    def __init__(self, data_type):
        """Initializes an empty database and start listening the endpoint."""
        LOG.info('Starting Writter')
        self.database = get_hdf5_file(data_type)
        store = HDFStore(self.database, complevel=9, complib='blosc')
        store.close()
        self.data_type = data_type
        self.lock = Lock()
        self.measurements = dict()
        """Creates all required directories."""
        try:
            os.makedirs(cfg.CONF.hdf5_dir)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise


    def update_hdf5(self, probe, data_type, timestamp, metrics, params):
        """Updates HDF5 file associated with this probe."""
        if not data_type == self.data_type:
            return
        if probe not in self.measurements:
            self.measurements[probe] = []
        self.measurements[probe].append((timestamp, metrics))
        if len(self.measurements[probe]) == 300:
            zipped = map(list, zip(*self.measurements[probe]))
            self.write_datas(probe,
                             data_type,
                             map(to_timestamp, np.array(zipped[0])),  # Timestp
                             np.array(zipped[1]))  # measures
            self.measurements[probe] = list()

    def write_datas(self, probe, data_type, timestamps, measures):
        """Stores data for this probe."""
        self.lock.acquire()
        print "AC", data_type
        try:
            path = get_probe_path(probe)
            s = TimeSeries(measures, index=timestamps)
            with get_store(self.database) as store:
                store.append(path, s)
                store.flush(fsync=True)
        except:
            LOG.error("Fail to add %s datas" % probe)
        finally:
            self.lock.release()
            print "RE", data_type

    def get_probes_list(self):
        probes = []
        self.lock.acquire()
        print "AC", self.data_type
        try:
            store = HDFStore(self.database)
            for k in store.keys():
                try:
                    # /site/host
                    _, site, host = k.split("/")
                    for probe in host.split('__'):
                        # /site/power/cluster/host => host.site.grid5000.fr
                        probes.append("%s.%s.grid5000.fr" % (probe.replace('_','-'), site))
                except:
                    LOG.error("Can't parse %s" % k)
            store.close()
        except:
            probes = []
        finally:
            self.lock.release()
            print "RE", self.data_type
        return probes

    def rotate(self):
        """
        Rotate the log file to write in the correct location
        This method is executed automatically after the timeout interval.
        """

        LOG.info('Rotate file')
        # Stop writings
        self.lock.acquire()
        print "AC", self.data_type
        # Retrieving last written values
        #TODO
        # Rotate file name
        self.database = get_hdf5_file(self.data_type)
        # Append missing values to new file
        #TODO
        # Schedule periodic execution of this function
        if cfg.CONF.cleaning_interval > 0:
            timer = Timer(3600.0, self.clean)
            timer.daemon = True
            timer.start()
        # Release lock
        self.lock.release()
        print "RE", self.data_type

    def select_probes_datas(self, probes, start_time, end_time):
        message = dict()
        self.lock.acquire()
        print "AC", self.data_type
        for probe in probes:
            path = get_probe_path(probe)
            if path:
                message[probe] = dict()
                message[probe]["uid"] = probe.split('.')[1]
                message[probe]["to"] =  int(end_time)
                message[probe]["from"] = int(start_time)
                try:
                    ts = read_hdf(self.database,
                                  path,
                                  where=["index>='%s'"%to_timestamp(start_time),
                                         "index<='%s'"%to_timestamp(end_time)])
                    message[probe]['values'] = list(ts.values)
                    message[probe]['timestamps'] = list(ts.index.astype(np.int64) // 10**9)
                except:
                    message[probe]['values'] = ['Unknown probe']
        self.lock.release()
        print "RE", self.data_type
        return message

def get_hdf5_file(data_type):
    return cfg.CONF.hdf5_dir + '/' + str(date.today().year)  + \
                               '_' + str(date.today().month) + \
                               '_' + str(data_type) + '_store.h5'


def to_timestamp(t):
    return to_datetime(t, unit='s')
