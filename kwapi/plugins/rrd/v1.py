# -*- coding: utf-8 -*-

"""This blueprint defines all URLs and answers."""

import os

import flask
from jinja2 import TemplateNotFound

from kwapi.openstack.common import cfg

blueprint = flask.Blueprint('v1', __name__)

@blueprint.route('/')
def welcome():
    """Shows specified page."""
    try:
        return flask.render_template('index.html', probes=flask.request.rrd_files.keys())
    except TemplateNotFound:
        flask.abort(404)

@blueprint.route('/<probe>/')
def chart(probe):
    """Sends chart."""
    try:
        rrd_file = flask.request.rrd_files[probe]
        png_file = os.path.dirname(rrd_file) + '/' + os.path.basename(rrd_file).replace('.rrd', '.png')
        return flask.send_file(png_file)
    except:
        flask.abort(404)
