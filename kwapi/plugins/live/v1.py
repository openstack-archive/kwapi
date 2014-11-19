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

import collections
import os
import shutil
import socket
import tempfile
import time
import zipfile

from execo_g5k.api_utils import get_resource_attributes
import flask
from flask import flash
from jinja2 import TemplateNotFound

from kwapi.utils import cfg
import live

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
    return flask.redirect(flask.url_for('v1.welcome_scale',
                                        metric='energy',
                                        scale='minute'))


@blueprint.route('/<metric>/last/<scale>/')
def welcome_scale(metric, scale):
    """Shows a specific scale of a probe."""
    if metric == 'energy':
        probes = flask.request.probes_power
    elif metric == 'network':
        probes = flask.request.probes_network
    else:
        flask.abort(404)
    # if live.contains_multiprobes(probes) and metric == 'energy':
    #    flash('Multiprobes somewhere!') 
    try:
        return flask.render_template('index.html',
                                     hostname=flask.request.hostname,
                                     metric=metric,
                                     probes=sorted(probes),
                                     #  key=lambda x: (x.split('.')[1].split('-')[0],
                                     #  int(x.split('.')[1].split('-')[1]))),
                                     refresh=cfg.CONF.refresh_interval,
                                     scales=flask.request.scales,
                                     scale=scale,
                                     start=int(time.time()) - flask.request.scales[scale][0]['interval'],
                                     end=int(time.time()),
                                     view='scale')
    except TemplateNotFound:
        flask.abort(404)


@blueprint.route('/<metric>/probe/<probe>/')
def welcome_probe(metric, probe):
    """Shows all graphs of a probe."""                                              
    if metric == 'energy':                                                     
        probes = flask.request.probes_power                                    
    elif metric == 'network':                                                  
        probes = flask.request.probes_network                                  
    else:                                                                      
        flask.abort(404) 
    if live.contains_multiprobes([probe]) and metric == 'energy':
        flash("Multiprobes somewhere !")
    if probe not in probes:
        flask.abort(404)
    try:
        scales = collections.OrderedDict()
        for scale in flask.request.scales:
            scales[scale] = {
                'start': int(time.time()) - flask.request.scales[scale][0]['interval'],
                'end': int(time.time())
            }
        return flask.render_template('index.html',
                                     hostname=flask.request.hostname,
                                     metric=metric,
                                     probe=probe,
                                     refresh=cfg.CONF.refresh_interval,
                                     scales=scales,
                                     view='probe')
    except TemplateNotFound:
        flask.abort(404)


@blueprint.route('/nodes/<job>/')
def get_nodes(job):
    """Returns nodes assigned to a job."""
    site = socket.getfqdn().split('.')
    site = site[1] if len(site) >= 2 else site[0]
    path = '/sites/' + site + '/jobs/' + job
    job_properties = get_resource_attributes(path)
    nodes = job_properties['assigned_nodes']
    try:
        started_at = job_properties['started_at']
    except KeyError:
        started_at = 'Undefined'
    try:
        stopped_at = job_properties['stopped_at']
    except KeyError:
        stopped_at = 'Undefined'
    return flask.jsonify({'job': int(job),
                          'started_at': started_at,
                          'stopped_at': stopped_at,
                          'nodes': nodes})


@blueprint.route('/zip/')
def send_zip():
    """Sends zip file."""
    probes = flask.request.args.get('probes')
    if probes:
        probes = probes.split(',')
    else:
        probes = flask.request.probes_power
    tmp_file = tempfile.NamedTemporaryFile()
    zip_file = zipfile.ZipFile(tmp_file.name, 'w')
    probes = [probe.encode('utf-8') for probe in probes
              if os.path.exists(live.get_rrd_filename(probe))]
    metrics = ['energy','network']
    print 'Zip', probes
    if len(probes) == 1:
        probe = probes[0]
        rrd_file = live.get_rrd_filename(probe)
        zip_file.write(rrd_file, '/rrd/' + probe + '.rrd')
        for scale in ['minute', 'hour', 'day', 'week', 'month', 'year']:
            for metric in metrics:
                png_file = live.build_graph(metric,
                                        int(time.time()) - flask.request.scales[scale][0]['interval'],
                                        int(time.time()),
                                        probe,
                                        False)
                zip_file.write(png_file, '/png/'+ metric + '/' + probe + '-' + scale + '.png')
    elif len(probes) > 1:
        for probe in probes:
            rrd_file = live.get_rrd_filename(probe)
            zip_file.write(rrd_file, '/rrd/' + probe + '.rrd')
            for scale in ['minute', 'hour', 'day', 'week', 'month', 'year']:
                for metric in metrics:
                    png_file = live.build_graph(metric,
                                            int(time.time()) - flask.request.scales[scale][0]['interval'],
                                            int(time.time()),
                                            probe,
                                            False)
                    zip_file.write(png_file, '/png/'+metric + '/' + probe + '/' + scale + '.png')
        # Separate energy and network
        for scale in ['minute', 'hour', 'day', 'week', 'month', 'year']:
            png_file_energy = live.build_graph('energy',
                                               int(time.time()) - flask.request.scales[scale][0]['interval'],
                                               int(time.time()),
                                               probes,
                                               True)
            zip_file.write(png_file_energy, '/png/summary-energy-' + scale + '.png')
            png_file_network = live.build_graph('network',
                                                int(time.time()) - flask.request.scales[scale][0]['interval'],
                                                int(time.time()),
                                                probes,
                                                True)
            zip_file.write(png_file_network, '/png/summary-network-' + scale + '.png')
    else:
        flask.abort(404)
    return flask.send_file(tmp_file,
                           as_attachment=True,
                           attachment_filename='rrd.zip',
                           cache_timeout=0,
                           conditional=True)


@blueprint.route('/<metric>/summary-graph/<start>/<end>/')
def send_summary_graph(metric,start, end):
    """Sends summary graph."""
    probes_list = []
    if metric == 'energy':                                                     
        probes_list = flask.request.probes_power                                    
    elif metric == 'network':                                                  
        probes_list = flask.request.probes_network                                  
    else:                                                                      
        flask.abort(404) 
    probes = flask.request.args.get('probes')
    if probes:
        probes = probes.split(',')
        probes = [probe.encode('utf-8') for probe in probes]
        for probe in probes:
            if probe not in probes_list:
                flask.abort(404)
    else:
        probes = list(probes_list)
    start = start.encode('utf-8')
    end = end.encode('utf-8')
    png_file = live.build_graph(metric, int(start), int(end), probes, True)
    if not png_file:
        flask.abort(404)
    tmp_file = tempfile.NamedTemporaryFile()
    shutil.copy2(png_file, tmp_file.name)
    if not png_file.endswith('summary-'+metric+'.png'):
        os.unlink(png_file)
    try:
        return flask.send_file(tmp_file,
                               mimetype='image/png',
                               cache_timeout=0,
                               conditional=True)
    except:
        flask.abort(404)


@blueprint.route('/<metric>/graph/<probe>/<start>/<end>/')
def send_probe_graph(metric, probe, start, end):
    """Sends graph."""
    probe = probe.encode('utf-8')
    start = start.encode('utf-8')
    end = end.encode('utf-8')
    png_file = live.build_graph(metric, int(start), int(end), probe, False)
    if not png_file:
        flask.abort(404)
    try:
        return flask.send_file(png_file, cache_timeout=0, conditional=True)
    except:
        flask.abort(404)
