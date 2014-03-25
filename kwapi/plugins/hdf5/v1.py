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

"""This blueprint defines all URLs and answers."""

import time
import flask
import socket
from execo_g5k import get_resource_attributes
from kwapi.utils import cfg, log
from pandas import read_hdf
from hdf5 import get_probe_path

LOG = log.getLogger(__name__)

web_opts = [
    cfg.StrOpt('hdf5_dir',
               required=True,
               ),
]
cfg.CONF.register_opts(web_opts)

blueprint = flask.Blueprint('v1', __name__)


@blueprint.route('/')
def welcome():
    """Returns detailed information about this specific version of the API."""
    return 'Welcome to Kwapi!'


@blueprint.route('/probe-ids/')
def list_probes_ids():
    """Returns all known probes IDs."""
    message = {}
    message['probe_ids'] = flask.request.collector.database.keys()
    response = flask.jsonify(message)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@blueprint.route('/metrics/')
def retrieve_measurements():
    """Returns measurements."""
    hostname = socket.getfqdn().split('.')
    site = hostname[1] if len(hostname) >= 2 else hostname[0]
    
    args = flask.request.args
    probes = None
    if 'job_id' in args:
        job_info = get_resource_attributes('sites/' + site + '/jobs/' + args['job_id'])
        start_time = job_info['started_at']
        end_time = start_time + job_info['walltime']
        nodes = list(set(job_info['resources_by_type']['cores'])) 
        probes = [site + '.' + node.split('.')[0] for node in nodes]
    elif 'probes' in args:
        LOG.info(args['probes'].split(','))
        probes = [site + '.' + node for node in args['probes'].split(',')]
        start_time = args['start_time'] if 'start_time' in args else time.time() - 24 * 3600
        end_time = args['end_time'] if 'end_time' in args else time.time()

    if probes:
        message = {'start_time': start_time, 'end_time': end_time, 'probes': {}}
        for probe in probes:
            message['probes'][probe] = []
            df = read_hdf(cfg.CONF.hdf5_dir + '/store.h5', get_probe_path(probe), 
                where=['index>=' +str(start_time), 'index<=' +str(end_time)])
            for ts, mes in df.iterrows():
                message['probes'][probe].append((ts, mes[0]))
            
    response = flask.jsonify(message)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response