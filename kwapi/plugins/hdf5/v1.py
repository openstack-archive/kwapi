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
from hdf5_collector import *

LOG = log.getLogger(__name__)
metrics = ['power', 'network_in', 'network_out']

web_opts = [
    cfg.StrOpt('hdf5_dir',
               required=True,
               ),
]
cfg.CONF.register_opts(web_opts)

blueprint = flask.Blueprint('v1', __name__)
hostname = socket.getfqdn().split('.')
site = hostname[1] if len(hostname) >= 2 else hostname[0]


@blueprint.route('/')
def welcome():
    message = {"items":[]}
    headers = flask.request.headers
    for metric in metrics:
        message["items"].append(get_type(metric,headers))
    response = flask.jsonify(message)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

def get_type(metric,headers):
    probe_list = []
    try:
        if metric == 'power':
            probe_list = flask.request.storePower.get_probes_list()
        elif metric == 'network_in':
            probe_list = flask.request.storeNetworkIn.get_probes_list()
        else :
            probe_list = flask.request.storeNetworkOut.get_probes_list()
    except:
        LOG.error("fail to retrieve probe list")
        return {}
    message = {'step': 1, 'available_on': probe_list, "type": "metric", "uid": metric,
               "links": [
            {
              "rel": "self",
              "type": "application/vnd.fr.grid5000.api.Metric+json;level=1",
              "href": _get_api_path(headers) + "sites/" + site
              + "/" + metric
           },
           {
              "title": "timeseries",
              "href": _get_api_path(headers) + "sites/" + site
              + "/" + metric + "/timeseries",
              "type": "application/vnd.fr.grid5000.api.Collection+json;level=1",
              "rel": "collection"
           },
           {
              "rel": "parent",
              "type": "application/vnd.fr.grid5000.api.Site+json;level=1",
              "href": _get_api_path(headers) + "sites/" + site
           }
        ],
        "timeseries": [
           {
              "xff": 0,
              "pdp_per_row": 1,
              "cf": "LAST"
           }]}
    return message

@blueprint.route('/<metric>/')
def welcome_type(metric):
    """Returns detailed information about this specific version of the API."""
    # Needs probe list
    if not metric in metrics:
        return flask.abort(404)
    headers = flask.request.headers
    message = get_type(metric,headers)
    response = flask.jsonify(message)
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
    if not metric in metrics:
        flask.abort(404)
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
                 "href": _get_api_path(headers) + "sites/" + site ,
                 "type": "application/vnd.fr.grid5000.api.Metric+json;level=1"
              }
           ],
                "items": [],
                }

        store = None
        try:
            if metric == 'power':
                store = flask.request.storePower
            elif metric == 'network_in':
                store = flask.request.storeNetworkIn
            else :
                store = flask.request.storeNetworkOut
        except:
            LOG.error("fail to retrieve store")
            flask.abort(404)
        items = store.select_probes_datas(probes, start_time, end_time)
        for item in items.values():
            message['items'].append({"uid": item["uid"],
                                  "to": item["to"],
                                  "from": item["from"],
                                  "resolution": 1,
                                  "type": "timeseries",
                                  "values": item["values"],
                                  "timestamps": item.get("timestamps", None),
                                  "links": [
                                      {
                                          "rel": "self",
                                          "href": _get_api_path(headers) +
                                          "sites/" + site + "/timeseries/" + item["uid"],
                                          "type": "application/vnd.fr.grid5000.api.Timeseries+json;level=1"
                                      },
                                      {
                                          "rel": "parent",
                                          "href": _get_api_path(headers) +
                                          "sites/" + site,
                                          "type": "application/vnd.fr.grid5000.api.Metric+json;level=1"
                                      }
                                  ]})
    response = flask.jsonify(message)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response
