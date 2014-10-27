import os
import errno
import socket
from pandas import HDFStore, DataFrame, get_store
from time import time
import numpy as np
from execo_g5k import get_host_cluster
from kwapi.utils import cfg, log
from datetime import date
import sys
from threading import Lock

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
lock = Lock()

def get_probe_path(probe, data_type):
    # Metric in the path
    if(data_type == 'power'):
        # site.probe-id
        # ex nancy.griffon-42
        site = probe.split(".")[0]
        host = probe.split(".")[1]
        cluster = get_host_cluster(host)
    else:
        # site.source-probe-id_dest-probe-id
        # ex nancy.griffon-42_sgriffon2
        site = probe.split(".")[0]
        host = probe.split(".")[1]
        # source cluster ?
        cluster = get_host_cluster(host.split("_")[0])
        if not cluster:
            # dest cluster ?
            cluster = get_host_cluster(host.split("_")[1])
        if not cluster:
            cluster = 'network_equipment'
    return "/%s/%s/%s/%s" % (site, data_type.replace('.', '_'), cluster, host.replace('_', "__").replace('-','_'))

def get_probes_list(data_type):
    hostname = socket.getfqdn().split('.')
    site = hostname[1] if len(hostname) >= 2 else hostname[0]
    probes = []
    lock.acquire()
    try:
        store = HDFStore(get_hdf5_file())
        for k in store.keys():
            try:
                # /site/data_type/cluster|network_equipment/host
                _, site, probe_data_type, cluster, host = k.split("/")
                if data_type == probe_data_type:
                    if data_type == 'power':
                        # /site/power/cluster/host => host.site.grid5000.fr
                        probes.append("%s.%s.grid5000.fr" % (host.replace('_','-'), site))
                    else:
                        # /site/energy/cluster|network_equipment/source-host_dest-host
                        # => host-source.site.grid5000.fr
                        host_source = host.split("__")[0]
                        probes.append("%s.%s.grid5000.fr" % (host_source.replace('_','-'), site))
            except:
                LOG.error("Can't parse %s" % k) 
        store.close()
    except:
        probes = []
    finally:
        lock.release()
    return probes

def get_hdf5_file():
    return cfg.CONF.hdf5_dir + '/' + str(date.today().year)  + \
                               '_' + str(date.today().month) + '_store.h5'

def create_dir():
    """Creates all required directories."""
    try:
        os.makedirs(cfg.CONF.hdf5_dir)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


def update_hdf5(probe, data_type, timestamp, metrics, params):
    """Updates HDF5 file associated with this probe."""
    if probe not in measurements:
        measurements[probe] = []
    measurements[probe].append((round(timestamp,0), metrics))
    if len(measurements[probe]) == 10:
        zipped = map(list, zip(*measurements[probe]))
        write_hdf5_file(probe,
                        data_type,
			np.array(zipped[0]), #timestamp
			np.array(zipped[1])) #measures
        measurements[probe] = list()

def write_hdf5_file(probe, data_type, timestamps, measurements):
    df = DataFrame(measurements, index=timestamps)
    path = get_probe_path(probe, data_type)
    lock.acquire()
    try:
        df.to_hdf(get_hdf5_file(), path, append = True)
    except:
        LOG.error('Unexpected error: %s' % sys.exc_info()[0])
    finally:
        lock.release()
