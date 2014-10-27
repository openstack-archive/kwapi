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

"""Defines functions to build and update rrd database and graph."""

import collections
import errno
import os
from threading import Lock
import struct
import time
import uuid

import rrdtool

from kwapi.utils import cfg, log

LOG = log.getLogger(__name__)

rrd_opts = [
    cfg.BoolOpt('signature_checking',
                required=True,
                ),
    cfg.IntOpt('hue',
               required=True,
               ),
    cfg.IntOpt('max_metrics',
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
    cfg.StrOpt('png_dir',
               required=True,
               ),
    cfg.StrOpt('rrd_dir',
               required=True,
               ),
]

cfg.CONF.register_opts(rrd_opts)

probes_set = set()
lock = Lock()

scales = collections.OrderedDict()
# Resolution = 1 second
scales['minute'] = {'interval': 300, 'resolution': 1, 'label': '5 minutes'},
# Resolution = 10 seconds
scales['hour'] = {'interval': 3600, 'resolution': 10, 'label': 'hour'},
# Resolution = 15 minutes
scales['day'] = {'interval': 86400, 'resolution': 900, 'label': 'day'},
# Resolution = 2 hours
scales['week'] = {'interval': 604800, 'resolution': 7200, 'label': 'week'},
# Resolution = 6 hours
scales['month'] = {'interval': 2678400, 'resolution': 21600, 'label': 'month'},
# Resolution = 1 week
scales['year'] = {'interval': 31622400, 'resolution': 604800, 'label': 'year'},

def create_dirs():
    """Creates all required directories."""
    directories = []
    directories.append(cfg.CONF.rrd_dir)
    # Build a list of directory names
    # Create each directory in a try block, and continue if directory already
    # exist
    for directory in directories:
        try:
            os.makedirs(directory)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

def get_rrd_filename(probe):
    """Returns the rrd filename."""
    # Include params in the path
    return cfg.CONF.rrd_dir + '/' + str(uuid.uuid5(uuid.NAMESPACE_DNS,
                                        str(probe))) + '.rrd'

def create_rrd_file(filename, params):
    """Creates a RRD file."""
    if not os.path.exists(filename):
        if params['type'] != 'Gauge':
            args = [filename,
                    '--start', '0',
                    '--step', '1',
                    # Heartbeat = 600 seconds, Min = 0, Max = Unlimited
                    'DS:o:DERIVE:600:0:U',
            ]
        else:
            args = [filename,
                    '--start', '0',
                    '--step', '1',
                    # Heartbeat = 600 seconds, Min = 0, Max = Unlimited
                    'DS:w:GAUGE:600:0:U',
            ]
        for scale in scales.keys():
            args.append('RRA:AVERAGE:0.5:%s:%s'
                        % (scales[scale][0]['resolution'],
                           scales[scale][0]['interval'] /
                           scales[scale][0]['resolution']))
        rrdtool.create(args)

def update_rrd(probe, data_type, timestamp, metrics, params):
    """Updates RRD file associated with this probe."""
    if not probe in probes_set:
         lock.acquire()
         probes_set.add(probe)
         lock.release()
    # Depends on data_type
    filename = get_rrd_filename(probe)
    if not os.path.isfile(filename):
        create_rrd_file(filename, params)
    try:
        rrdtool.update(filename, '%d:%d' % (round(timestamp,0), metrics))
    except:
        LOG.error('Error updating RRD: %s %s' % (timestamp, metrics))

