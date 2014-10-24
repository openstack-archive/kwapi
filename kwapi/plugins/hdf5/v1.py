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
from hdf5 import get_probe_path, get_probes_list, get_hdf5_file, lock

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
    return flask.redirect(flask.url_for('v1.welcome_type',
                                        metric='power'))

@blueprint.route('/<metric>/')
def welcome_type(metric):
    """Returns detailed information about this specific version of the API."""

    headers = flask.request.headers
    hostname = socket.getfqdn().split('.')
    site = hostname[1] if len(hostname) >= 2 else hostname[0]
    message = {'step': 1, 'available_on': get_probes_list(metric), "type": "metric",
               "links": [
            {
              "rel": "self",
              "type": "application/vnd.fr.grid5000.api.Metric+json;level=1",
              "href": _get_api_path(headers) + "/sites/" + site
              + "/" + metric
           },
           {
              "title": "timeseries",
              "href": _get_api_path(headers) + "/sites/" + site
              + "/" + metric + "/timeseries",
              "type": "application/vnd.fr.grid5000.api.Collection+json;level=1",
              "rel": "collection"
           },
           {
              "rel": "parent",
              "type": "application/vnd.fr.grid5000.api.Site+json;level=1",
              "href": _get_api_path(headers) + "/sites/" + site
           }
        ],
        "timeseries": [
           {
              "rows": 244,
              "xff": 0.5,
              "pdp_per_row": 1,
              "cf": "AVERAGE"
           }]}
    response = flask.jsonify(message)
    LOG.info(response)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


def _get_api_path(headers):
    """Create the path to be included for the rest syntax"""
    return "/" + headers.get('HTTP_X_API_VERSION', 'sid') + \
        headers.get('HTTP_X_API_PREFIX', '') + '/'


# @blueprint.route('/probe-ids/')
# def show_probes():
#     """Returns all known probes IDs."""
#     message = {'probes_list': probes_list()}
#     response = flask.jsonify(message)
#     response.headers.add('Access-Control-Allow-Origin', '*')
#     return response


@blueprint.route('/<metric>/timeseries/')
def retrieve_measurements(metric):
    """Returns measurements."""
    headers = flask.request.headers
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
        probes = [site + '.' + node for node in args['probes'].split(',')]
        start_time = args['start_time'] if 'start_time' in args else time.time() - 24 * 3600
        end_time = args['end_time'] if 'end_time' in args else time.time()
    else:
        LOG.info('No probes or job_id given')
        return 'No probes or job_id given, use \n '

    if probes:
        message = {'total': len(probes), 'offset': 0, 'links': [
              {
                 "rel": "self",
                 "href": _get_api_path(headers) + site,
                 "type": "application/vnd.fr.grid5000.api.Collection+json;level=1"
              },
              {
                 "rel": "parent",
                 "href": _get_api_path(headers) + "/sites/" + site ,
                 "type": "application/vnd.fr.grid5000.api.Metric+json;level=1"
              }
           ],
                "items": [],
                }

        LOG.info(','.join(probes))
        for probe in probes:
            path = get_probe_path(probe, metric)
            print path
            if path:
                message['items'].append({"uid": probe.split('.')[1],
                            "to": int(end_time),
                            "from": int(start_time),
                            "resolution": 1,
                            "type": "timeseries",
                            "values": [],
                            "timestamps": [],
                            "links": [
                    {
                        "rel": "self",
                        "href": _get_api_path(headers) +
                        "/sites/" + site + "/timeseries/" +probe.split('.')[1],
                        "type": "application/vnd.fr.grid5000.api.Timeseries+json;level=1"
                    },
                    {
                        "rel": "parent",
                        "href": _get_api_path(headers) +
                        "/sites/" + site,
                        "type": "application/vnd.fr.grid5000.api.Metric+json;level=1"
                    }
                ]})
                lock.acquire()
                try:
                    df = read_hdf(get_hdf5_file(),
                         path,
                         where=['index>=' + str(start_time),
                                'index<=' + str(end_time)])
                    for ts, mes in df.iterrows():
                        message['items'][-1]['values'].append(mes[0])
                        message['items'][-1]['timestamps'].append(ts)
                except:
                    message['items'][-1]['values'] = ['Unknown probe']
                finally:
                    lock.release()
    response = flask.jsonify(message)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response
