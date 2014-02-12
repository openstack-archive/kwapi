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

"""Defines functions to build and update hdf5 files."""



from kwapi.utils import cfg, log
from kwapi.plugins import listen
import zmq



LOG = log.getLogger(__name__)


def create_probe_dir(probe):
    """Creates all required directories."""
    probe_dir = cfg.CONF.hdf5_dir +get_host_cluster(probe.split('.')[1])
    try:
       os.makedirs(probe_dir)
    except OSError as exception:
       if exception.errno != errno.EEXIST:
           raise
    return probe_dir            
            
def create_hdf5_file(probe):
    """ """ 
    probe_dir = create_probe_dir(probe)
    f = h5py.File(probe_dir+probe+'.hdf5','w')
    
    f.close()
    
    
    


def update_hdf5_file(probe, measurements):
    """A method to add data t """
    
    # if not file exists 
    
    # open it
    
    
                

