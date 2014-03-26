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

import os
import shutil
import socket
import tempfile
import zipfile

from execo_g5k.api_utils import get_resource_attributes
import flask
from jinja2 import TemplateNotFound

from kwapi.utils import cfg
import rrd

web_opts = [
    cfg.IntOpt('refresh_interval',
               required=True,
               ),
    cfg.StrOpt('png_dir',
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


@blueprint.route('/nodes/<job>/')
def get_nodes(job):
    """Returns nodes assigned to a job."""
    site = socket.getfqdn().split('.')
    site = site[1] if len(site) >= 2 else site[0]
    path = '/sites/' + site + '/jobs/' + job
    nodes = get_resource_attributes(path)['assigned_nodes']
    return flask.jsonify({'job': job, 'nodes': nodes})


@blueprint.route('/zip/')
def send_zip():
    """Sends zip file."""
    probes = flask.request.args.get('probes')
    if probes:
        probes = probes.split(',')
    else:
        probes = flask.request.probes
    tmp_file = tempfile.NamedTemporaryFile()
    zip_file = zipfile.ZipFile(tmp_file.name, 'w')
    probes = [probe.encode('utf-8') for probe in probes
              if os.path.exists(rrd.get_rrd_filename(probe))]
    if len(probes) == 1:
        probe = probes[0]
        rrd_file = rrd.get_rrd_filename(probe)
        zip_file.write(rrd_file, '/rrd/' + probe + '.rrd')
        for scale in ['minute', 'hour', 'day', 'week', 'month', 'year']:
            png_file = rrd.build_graph(scale, probe, False)
            zip_file.write(png_file, '/png/' + probe + '-' + scale + '.png')
    elif len(probes) > 1:
        for probe in probes:
            rrd_file = rrd.get_rrd_filename(probe)
            zip_file.write(rrd_file, '/rrd/' + probe + '.rrd')
            for scale in ['minute', 'hour', 'day', 'week', 'month', 'year']:
                png_file = rrd.build_graph(scale, probe, False)
                zip_file.write(png_file, '/png/' + probe + '/' + scale + '.png')
        for scale in ['minute', 'hour', 'day', 'week', 'month', 'year']:
            png_file = rrd.build_graph(scale, probes, True)
            zip_file.write(png_file, '/png/summary-' + scale + '.png')
    else:
        flask.abort(404)
    return flask.send_file(tmp_file,
                           as_attachment=True,
                           attachment_filename='rrd.zip',
                           cache_timeout=0,
                           conditional=True)


@blueprint.route('/graph/<scale>/')
def send_summary_graph(scale):
    """Sends summary graph."""
    probes = flask.request.args.get('probes')
    if probes:
        probes = probes.split(',')
        probes = [probe.encode('utf-8') for probe in probes]
        for probe in probes:
            if probe not in flask.request.probes:
                flask.abort(404)
    else:
        probes = list(flask.request.probes)
    scale = scale.encode('utf-8')
    png_file = rrd.build_graph(scale, probes, True)
    tmp_file = tempfile.NamedTemporaryFile()
    shutil.copy2(png_file, tmp_file.name)
    if png_file != cfg.CONF.png_dir + '/' + scale + '/summary.png':
        os.unlink(png_file)
    try:
        return flask.send_file(tmp_file,
                               mimetype='image/png',
                               cache_timeout=0,
                               conditional=True)
    except:
        flask.abort(404)


@blueprint.route('/graph/<scale>/<probe>/')
def send_probe_graph(scale, probe):
    """Sends graph."""
    probe = probe.encode('utf-8')
    scale = scale.encode('utf-8')
    png_file = rrd.build_graph(scale, probe, False)
    try:
        return flask.send_file(png_file, cache_timeout=0, conditional=True)
    except:
        flask.abort(404)
