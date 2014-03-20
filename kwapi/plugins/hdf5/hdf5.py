from pandas import HDFStore, DataFrame
from random import randint
from time import time
import numpy as np
from execo_g5k import get_host_cluster, get_cluster_hosts
from execo import Timer, sleep

from kwapi.utils import cfg, log

LOG = log.getLogger(__name__)

measurements = {}

def get_probe_path(probe):
    cluster = get_host_cluster(probe)
    return cluster + '/' + probe.replace('-', '_')

def create_probe_dir(probe):
    """Creates all required directories."""
    probe_dir = cfg.CONF.hdf5_dir
    try:
       os.makedirs(probe_dir)
    except OSError as exception:
       if exception.errno != errno.EEXIST:
           raise
    return probe_dir
            
def create_hdf5_file():
    """Creates a HDF5 file."""
    probe_dir = create_probe_dir(probe)
    f = h5py.File(probe_dir + 'store.h5', 'w')
    f.close()
    
def update_hdf5(probe, watts):
    """Updates HDF5 file associated with this probe."""
    if probe not in measurements:
        measurements[probe] = []
    measurements[probe].append((int(time()), watts))
    if len(measurements[probe]) > 10:
        thread.start_new_thread(write_hdf5_file, ())
        
def write_hdf5_file():
    for probe in measurements.keys():
        zipped = zip(*measurements)
        df = DataFrame(np.array(zipped[1]), index=np.array(zipped[0]))
        path = get_probe_path(probe)
        store.append(path, df)