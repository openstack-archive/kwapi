# -*- coding: utf-8 -*-

"""This blueprint defines all URLs and answers."""

import hashlib
import hmac

import flask

from kwapi.openstack.common import cfg

blueprint = flask.Blueprint('v1', __name__)

@blueprint.route('/')
def welcome():
    """Returns detailed information about this specific version of the API."""
    return 'Welcome to Kwapi!'

@blueprint.route('/probe-ids/')
def list_probes_ids():
    """Returns all known probes IDs."""
    message = {}
    message['probe_ids'] = flask.request.database.keys()
    return flask.jsonify(message)

@blueprint.route('/probes/')
def list_probes():
    """Returns all information about all known probes."""
    message = {}
    message['probes'] = flask.request.database
    return flask.jsonify(message)

@blueprint.route('/probes/<probe>/')
def probe_info(probe):
    """Returns all information about this probe (id, timestamp, kWh, W)."""
    message = {}
    try:
        message[probe] = flask.request.database[probe]
    except KeyError:
        flask.abort(404)
    return flask.jsonify(message)

@blueprint.route('/probes/<probe>/<meter>/')
def probe_value(probe, meter):
    """Returns the probe meter value."""
    message = {}
    try:
        message[probe] = {meter: flask.request.database[probe][meter]}
    except KeyError:
        flask.abort(404)
    return flask.jsonify(message)
