import os
import errno
import socket
import numpy as np
from kwapi.utils import cfg, log
from threading import Lock, Timer
from datetime import datetime
from dateutil.relativedelta import relativedelta
from Queue import Queue
import gc
import psutil
from tables import *

def print_memory(m=None):
    p = psutil.Process(os.getpid())
    (rss, vms) = p.get_memory_info()
    mp = p.get_memory_percent()
    print("%-10.10s cur_mem->%.2f (MB),per_mem->%.2f" % (m, rss / 1000000.0, mp))

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
# One queue per metric
buffered_values = {
    "power": Queue(600),
    "network_in" : Queue(600),
    "network_out": Queue(600),
}

def update_hdf5(probe, data_type, timestamp, metrics, params):
    """Updates HDF5 file associated with this probe."""
    if not data_type in buffered_values:
        return
    buffered_values[data_type].put((probe, timestamp, metrics))


def get_probe_path(probe):
    host = probe.split(".")[1]
    return "/%s/%s" % (site, host.replace('_', "__").replace('-', '_'))


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
        self.save_date = datetime.strptime(cfg.CONF.start_date, "%Y/%m/%d")
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
        store = openFile(self.database, mode="w", title = "Fine grained measures")
        store.close()

    def get_hdf5_file(self):
        if self.next_save_date <= datetime.now():
            self.save_date = self.next_save_date
            self.next_save_date += self.delta
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
                #print "size %d" % buffered_values[self.data_type].qsize()
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
        f = open_file(self.database, mode = "a")
        try:
            path = get_probe_path(probe)
            if not path in f:
                _, cluster, probe = path.split('/')
                if not group in f.root:
                    group = f.create_group("/", cluster, "cluster")
                if not path in f:
                    table = f.create_table(group, probe, ProbeMeasures, "probe")
            table = f.get_node(path)
            for x in range(len(timestamps)):
                table.row['timestamp'] = timestamps[x]
                table.row['measure'] = measures[x]
                table.row.append()
            table.flush()
        except:
            LOG.error("Fail to add %s datas" % probe)
        finally:
            f.flush()
            f.close()
            self.lock.release()
            #print_memory("write2 %s" % probe)
            #print gc.collect(),
            #print gc.collect()
            #print_memory("gc2 %s" % probe)

    def get_probes_list(self):
        probes = []
        self.lock.acquire()
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
        return probes

    def rotate(self):
        """
        Rotate the log file to write in the correct location
        This method is executed automatically after the timeout interval.
        """

        LOG.info('Rotate file')
        # Stop writings
        self.lock.acquire()
        # Rotate file name
        old_database = str(self.database)
        old_save = self.next_save_date
        self.database = self.get_hdf5_file()
        #TODO Finish implementation
        #if not self.database == old_database:
        #    # Retrieving last written values
        #    old_store = HDFStore(old_database)
        #    for k in old_store.keys():
        #        ts = read_hdf(old_database,
        #                      k,
        #                      where="index>'%s'"%old_save)
        #        # Append missing values to new file
        #        with get_store(self.database) as new_store:
        #            new_store.append(k, ts)
        #            new_store.flush(fsync=True)

        # Schedule periodic execution of this function
        timer = Timer(3600.0, self.rotate)
        timer.daemon = True
        timer.start()
        # Release lock
        self.lock.release()

    def select_probes_datas(self, probes, start_time, end_time):
        message = dict()
        self.lock.acquire()
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
                                  where=["index>='%s'"%to_datetime(start_time, unit='s'),
                                         "index<='%s'"%to_datetime(end_time, unit='s')])
                    message[probe]['values'] = list(ts.values)
                    message[probe]['timestamps'] = list(ts.index.astype(np.int64) // 10**9)
                except:
                    message[probe]['values'] = ['Unknown probe']
        self.lock.release()
        return message
