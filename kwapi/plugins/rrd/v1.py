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

from kwapi.utils import cfg
import rrd

web_opts = [
    cfg.IntOpt('refresh_interval',
               required=True,
               ),
]

cfg.CONF.register_opts(web_opts)

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
                                     hostname=flask.request.hostname,
                                     probes=sorted(flask.request.probes),
                                     refresh=cfg.CONF.refresh_interval,
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
                                     hostname=flask.request.hostname,
                                     probe=probe,
                                     refresh=cfg.CONF.refresh_interval,
                                     scales=flask.request.scales,
                                     view='probe')
    except TemplateNotFound:
        flask.abort(404)


@blueprint.route('/rrd/<probe>/')
def send_rrd(probe):
    """Sends summary graph."""
    probe = probe.encode('utf-8')
    rrd_file = rrd.get_rrd_filename(probe)
    try:
        return flask.send_file(rrd_file,
                               as_attachment=True,
                               attachment_filename=probe + '.rrd',
                               cache_timeout=0,
                               conditional=True)
    except:
        flask.abort(404)


@blueprint.route('/graph/<scale>/')
def send_summary_graph(scale):
    """Sends summary graph."""
    scale = scale.encode('utf-8')
    png_file = rrd.build_graph(scale)
    try:
        return flask.send_file(png_file, cache_timeout=0, conditional=True)
    except:
        flask.abort(404)


@blueprint.route('/graph/<scale>/<probe>/')
def send_probe_graph(scale, probe):
    """Sends graph."""
    probe = probe.encode('utf-8')
    scale = scale.encode('utf-8')
    png_file = rrd.build_graph(scale, probe)
    try:
        return flask.send_file(png_file, cache_timeout=0, conditional=True)
    except:
        flask.abort(404)
