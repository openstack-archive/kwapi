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

import flask

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
    return flask.jsonify(message)


@blueprint.route('/probes/')
def list_probes():
    """Returns all information about all known probes."""
    message = {}
    message['probes'] = flask.request.collector.database
    result = flask.jsonify(message)
    return result


@blueprint.route('/probes/<probe>/')
def probe_info(probe):
    """Returns all information about this probe (id, timestamp, kWh, W)."""
    message = {}
    try:
        message[probe] = flask.request.collector.database[probe]
    except KeyError:
        flask.abort(404)
    return flask.jsonify(message)


@blueprint.route('/probes/<probe>/<meter>/')
def probe_value(probe, meter):
    """Returns the probe meter value."""
    message = {}
    try:
        message[probe] = \
            {
                meter: flask.request.collector.database[probe][meter]
            }
    except KeyError:
        flask.abort(404)
    return flask.jsonify(message)
