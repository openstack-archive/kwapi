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

def get_probe_path(probe):
    site = probe.split(".")[0]
    node = probe.split(".")[1].replace("-","_")
    return "/%s/%s" % (site, node)

def get_probe_path_network(probe, data_type, flow, dest):
    site = probe.split(".")[0]
    node = probe.split(".")[1]
    dest = dest.split(".")[1]
    if node:
        return "%s/%s/%s/%s/%s" \
               % (site, node.replace('-', '_'), data_type, flow, dest)


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


def update_hdf5(probe, data_type, timestamp, metrics, params):
    """Updates HDF5 file associated with this probe."""
    flow = params['flow'] #in or out
    dest = params['dest'] #traffic destination
    if probe not in measurements:
        measurements[probe] = dict()
    if not measurements[probe].has_key(data_type):
        measurements[probe][data_type] = dict()
    if not measurements[probe][data_type].has_key(flow):
        measurements[probe][data_type][flow] = dict()
    if not measurements[probe][data_type][flow].has_key(dest):
        measurements[probe][data_type][flow][dest] = list()
    measurements[probe][data_type][flow][dest].append((timestamp, metrics))
    if len(measurements[probe][data_type][flow][dest]) == 10:
        zipped = map(list, zip(*measurements[probe][data_type][flow][dest]))
        LOG.debug('%s %s', zipped[0], zipped[1])
        write_hdf5_file(probe,
			data_type,
			flow,
			dest,
			np.array(zipped[0]), #timestamp
			np.array(zipped[1])) #measures
        measurements[probe][data_type][flow][dest] = list()


def write_hdf5_file(probe, data_type, flow, dest, timestamps, measurements):
    store = HDFStore(cfg.CONF.hdf5_dir + '/store.h5')
    df = DataFrame(measurements, index=timestamps)
    path = get_probe_path_network(probe, data_type, flow, dest)
    store.append(path, df)
    store.close()
