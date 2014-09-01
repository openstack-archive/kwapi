import os
import errno
import socket
from pandas import HDFStore, DataFrame
from time import time
import numpy as np
from execo_g5k import get_host_cluster
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
site = socket.getfqdn().split('.')[1]

def get_probe_path(probe, type):
    node = probe.replace('->','__')
    #cluster = get_host_cluster(host)
    if node:
        return site + '/' + node.replace('-', '_') + '/' + type


def get_probes_list():
    hostname = socket.getfqdn().split('.')
    site = hostname[1] if len(hostname) >= 2 else hostname[0]
    probes = []
    store = HDFStore(cfg.CONF.hdf5_dir + '/store.h5')
    for df in store.keys():
        _, cluster, host = df.split('/')
        radicals = host.split('_')[1:]
        for radical in radicals:
            probes.append(cluster + '-' + radical + '.' + site + '.grid5000.fr')
    return probes


def create_dir():
    """Creates all required directories."""
    try:
        os.makedirs(cfg.CONF.hdf5_dir)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


def update_hdf5(probe, type, metrics):
    """Updates HDF5 file associated with this probe."""
    if probe not in measurements:
        measurements[probe] = dict()
    if not measurements[probe].has_key(type):
        measurements[probe][type] = list()
    measurements[probe][type].append((round(time(), 3), metrics))
    if len(measurements[probe][type]) == 10:
        zipped = map(list, zip(*measurements[probe][type]))
        LOG.debug('%s %s', zipped[0], zipped[1])
        write_hdf5_file(probe, type, np.array(zipped[0]), np.array(zipped[1]))
        measurements[probe][type] = list()


def write_hdf5_file(probe, type, timestamps, measurements):
    store = HDFStore(cfg.CONF.hdf5_dir + '/store.h5')
    df = DataFrame(measurements, index=timestamps)
    path = get_probe_path(probe, type)
    store.append(path, df)
    store.close()
