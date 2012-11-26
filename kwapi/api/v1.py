# -*- coding: utf-8 -*-

"""This blueprint defines all URLs and answers."""

import hashlib
import hmac

import flask
import flask.helpers

from kwapi import config

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
    sign(message)
    return flask.jsonify(message)

@blueprint.route('/probes/')
def list_probes():
    """Returns all information about all known probes."""
    message = {}
    message['probes'] = flask.request.database
    sign(message)
    return flask.jsonify(message)

@blueprint.route('/probes/<probe>/')
def probe_info(probe):
    """Returns all information about this probe (id, timestamp, kWh, W)."""
    message = {}
    try:
        message[probe] = flask.request.database[probe]
    except KeyError:
        flask.abort(404)
    sign(message)
    return flask.jsonify(message)

@blueprint.route('/probes/<probe>/<meter>/')
def probe_value(probe, meter):
    """Returns the probe meter value."""
    message = {}
    try:
        message[probe] = {meter: flask.request.database[probe][meter]}
    except KeyError:
        flask.abort(404)
    sign(message)
    return flask.jsonify(message)

def recursive_keypairs(dictionary):
    """Generator that produces sequence of keypairs for nested dictionaries."""
    for name, value in sorted(dictionary.iteritems()):
        if isinstance(value, dict):
            for subname, subvalue in recursive_keypairs(value):
                yield ('%s:%s' % (name, subname), subvalue)
        else:
            yield name, value

def sign(message):
    """Sets the message signature key."""
    digest_maker = hmac.new(config.CONF['api_metering_secret'], '', hashlib.sha256)
    for name, value in recursive_keypairs(message):
        if name != 'message_signature':
            digest_maker.update(name)
            digest_maker.update(unicode(value).encode('utf-8'))
    message['message_signature'] = digest_maker.hexdigest()
