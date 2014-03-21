import os
import thread
import errno
from pandas import HDFStore, DataFrame
from random import randint
from time import time
import numpy as np
from execo_g5k import get_host_cluster, get_cluster_hosts
from execo import Timer, sleep

from kwapi.utils import cfg, log

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


measurements = {}

def get_probe_path(probe):
    host = probe.split('.')[1]
    cluster = get_host_cluster(host)
    
    return cluster + '/' + host.replace('-', '_')

def create_dir():
    """Creates all required directories."""
    try:
       os.makedirs(cfg.CONF.hdf5_dir)
    except OSError as exception:
       if exception.errno != errno.EEXIST:
           raise
       
    
def update_hdf5(probe, watts):
    """Updates HDF5 file associated with this probe.""" 
    if probe not in measurements:
        measurements[probe] = []
    measurements[probe].append((round(time(), 3), watts))
    if len(measurements[probe]) == 10:
        zipped = map(list, zip(*measurements[probe]))
        LOG.info('%s %s', zipped[0], zipped[1])
        write_hdf5_file(probe, np.array(zipped[0]), np.array(zipped[1]))
        measurements[probe] = []
        

def write_hdf5_file(probe, timestamps, measurements):
    store = HDFStore(cfg.CONF.hdf5_dir + '/store.h5')
    df = DataFrame(measurements, index=timestamps)
    path = get_probe_path(probe)
    store.append(path, df)
    store.close()
