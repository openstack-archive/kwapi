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

"""Set up the HDF5 server application instance."""

import sys, signal
import thread
from threading import Thread

from kwapi.plugins import listen
from kwapi.utils import cfg, log
from hdf5_collector import HDF5_Collector
import hdf5_collector

LOG = log.getLogger(__name__)

app_opts = [
    cfg.MultiStrOpt('probes_endpoint',
                    required=True,
                    ),
    cfg.StrOpt('hdf5_dir',
               required=True,
               ),
    cfg.StrOpt('log_file',
               required=True,
               ),
]

cfg.CONF.register_opts(app_opts)

writters = []

def signal_handler(signal, frame):
    LOG.info("FLUSH DATAS")
    for data_type in hdf5_collector.buffered_values:
        hdf5_collector.buffered_values[data_type].put('STOP')
    for writter in writters:
        writter.join()
        LOG.info("DATA from %s FLUSHED" % writter.name)
        writter = None
    sys.exit(0)

def start():
    """Starts Kwapi HDF5."""
    cfg.CONF(sys.argv[1:],
             project='kwapi',
             default_config_files=['/etc/kwapi/hdf5.conf'])
    log.setup(cfg.CONF.log_file)
    LOG.info('Starting HDF5')
    storePower = HDF5_Collector('power')
    storeNetworkIn = HDF5_Collector('network_in')
    storeNetworkOut = HDF5_Collector('network_out')


    thread.start_new_thread(listen, (hdf5_collector.update_hdf5,))
    writters.append(Thread(target=storePower.write_datas,name="PowerWritter"))
    writters.append(Thread(target=storeNetworkIn.write_datas,name="NetworkInWritter"))
    writters.append(Thread(target=storeNetworkOut.write_datas,name="NetworkOutWritter"))
    for writter in writters:
        writter.daemon = True
        writter.start()

    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()

