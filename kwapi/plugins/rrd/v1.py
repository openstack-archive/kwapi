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
from jinja2 import TemplateNotFound

import rrd

blueprint = flask.Blueprint('v1', __name__, static_folder='static')


@blueprint.route('/')
def welcome():
    """Shows specified page."""
    return flask.redirect('/last/minute/')


@blueprint.route('/last/<scale>/')
def welcome_scale(scale):
    if scale not in flask.request.scales:
        flask.abort(404)
    try:
        return flask.render_template('index.html',
                                     probes=sorted(flask.request.probes),
                                     scales=flask.request.scales,
                                     scale=scale,
                                     view='scale')
    except TemplateNotFound:
        flask.abort(404)


@blueprint.route('/probe/<probe>/')
def welcome_probe(probe):
    if probe not in flask.request.probes:
        flask.abort(404)
    try:
        return flask.render_template('index.html',
                                     probe=probe,
                                     scales=flask.request.scales,
                                     view='probe')
    except TemplateNotFound:
        flask.abort(404)


@blueprint.route('/graph/<scale>/')
def send_summary_graph(scale):
    """Sends summary graph."""
    scale = scale.encode('utf-8')
    png_file = rrd.build_graph(scale)
    try:
        return flask.send_file(png_file)
    except:
        flask.abort(404)


@blueprint.route('/graph/<scale>/<probe>/')
def send_probe_graph(scale, probe):
    """Sends graph."""
    probe = probe.encode('utf-8')
    scale = scale.encode('utf-8')
    png_file = rrd.build_graph(scale, probe)
    try:
        return flask.send_file(png_file)
    except:
        flask.abort(404)
