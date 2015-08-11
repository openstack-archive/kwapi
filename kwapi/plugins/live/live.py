# -*- coding: utf-8 -*-
#
# Author: Clement Parisot <clement.parisot@inria.fr>
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
# License for the speci0.fic language governing permissions and limitations
# under the License.

"""Defines functions to visualize rrd graphs."""

import collections
import colorsys
import errno
import os
from threading import Lock
import struct
import time
import uuid
import ast
import re
import socket
from tempfile import NamedTemporaryFile

import rrdtool
from kwapi.plugins.rrd.rrd import get_rrd_filename, get_png_filename

from kwapi.utils import cfg, log
from socket import getfqdn
from execo_g5k.topology import g5k_graph
from execo_g5k import get_host_attributes, get_resource_attributes
import networkx as nx

LOG = log.getLogger(__name__)

live_opts = [
    cfg.FloatOpt('kwh_price',
                 required=True,
                 ),
    cfg.StrOpt('currency',
               required=True,
               ),
    cfg.BoolOpt('signature_checking',
                required=True,
                ),
    cfg.IntOpt('hue',
               required=True,
               ),
    cfg.IntOpt('max_metrics',
               required=True,
               ),
    cfg.MultiStrOpt('probes_endpoint',
                    required=True,
                    ),
    cfg.MultiStrOpt('watch_probe',
                    required=False,
                    ),
    cfg.StrOpt('driver_metering_secret',
               required=True,
               ),
    cfg.StrOpt('png_dir',
               required=True,
               ),
    cfg.StrOpt('rrd_dir',
               required=True,
               ),
]

cfg.CONF.register_opts(live_opts)

scales = collections.OrderedDict()
# Resolution = 1 second
scales['minute'] = {'interval': 300, 'resolution': 15, 'label': '5 minutes'},
# Resolution = 10 seconds
scales['hour'] = {'interval': 3600, 'resolution': 20, 'label': 'hour'},
# Resolution = 15 minutes
scales['day'] = {'interval': 86400, 'resolution': 900, 'label': 'day'},
# Resolution = 2 hours
scales['week'] = {'interval': 604800, 'resolution': 7200, 'label': 'week'},
# Resolution = 6 hours
scales['month'] = {'interval': 2678400, 'resolution': 21600, 'label': 'month'},
# Resolution = 1 week
scales['year'] = {'interval': 31622400, 'resolution': 604800, 'label': 'year'},

# One probe set per metric (displayed on web interface)
probes_set_network = set()
probes_set_power = set()
all_uid_power = set()

# Loads topology from config file.
parser = cfg.ConfigParser('/etc/kwapi/live.conf', {})
parser.parse()
hostname = socket.getfqdn().split('.')
site = hostname[1] if len(hostname) >= 2 else hostname[0]

# Mapping between name and probes
probes_names_maps = {}

def find_multi_probe(probe_name, data_type):
    """Return probe_uid attached to probe name if any.

    If no probe is attached to probe_name, return None.

    >>> find_multi_probe("nancy.griffon-1")
    nancy.griffon-1-2-3-...-x #corresponding pdu ID
    """
    try:
        return probes_names_maps[data_type].neighbors(probe_name)
    except:
        return []

def find_probe_uid(metric, probe_name):
    """Return probe_uid corresponding to given name and metric

    Power
    >>> find_probe_uid("power", "nancy.griffon-1")
    ['nancy.griffon-1-2-3-...-x']

    Network
    >>> find_probe_uid("network", "nancy.griffon-1")
    ['nancy.sgriffon1.1-1',]

    >>> find_probe_uid("network", "nancy.sgriffon-1")
    ['nancy.gw-nancy.1-1', 'nancy.sgriffon-2.1-1']
    """
    if metric == 'power':
        probe_uid = find_multi_probe(probe_name, 'power')
        return probe_uid
    if metric == 'network':
        try:
            res = probes_names_maps['network_in'].neighbors(probe_name)
        except:
            res = []
        return res

def get_rrds_from_name(probe_name, data_type):
    multi_probes_selected = find_multi_probe(probe_name, data_type)
    probes_uid = list(multi_probes_selected)
    probes_uid = map(get_rrd_filename, probes_uid, [data_type]*len(probes_uid))
    return probes_uid

probe_colors = {}
lock = Lock()

def create_dirs():
    """Creates all required directories."""
    directories = []
    directories.append(cfg.CONF.png_dir)
    # Build a list of directory names
    # Avoid loop in try block (problem if exception occurs), and avoid multiple
    # try blocks (too long)
    for scale in scales.keys():
        directories.append(cfg.CONF.png_dir + '/' + scale)
    # Create each directory in a try block, and continue if directory already
    # exist
    for directory in directories:
        try:
            os.makedirs(directory)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise


def create_color_gen():
    """Creates colors generator"""
    color_seq = color_generator(len(all_uid_power)+1)
    for probe in sorted(all_uid_power, reverse=True):
        probe_colors[probe] = color_seq.next()

def update_probe(probe, probes_names, data_type, timestamp, metrics, params):
    probe_short_uid = ".".join(probe.split(".")[:2]) # without ports
    if data_type in probes_names_maps:
        probes_names_maps[data_type].add_edge(probe_short_uid, probe)
    else:
        probes_names_maps[data_type] = nx.Graph()
        probes_names_maps[data_type].add_edge(probe_short_uid, probe)
    if data_type == 'power':
        probes_set_power.add(probe_short_uid)
        all_uid_power.add(probe_short_uid)
    else:
        probes_set_network.add(probe_short_uid)
    if not type(probes_names) == list:
        probes_names = list(probes_names)
    for probe_name in probes_names:
        probes_names_maps[data_type].add_edge(probe_name,probe)
        if data_type == 'power':
            probes_set_power.add(probe_name)
        else:
            probes_set_network.add(probe_name)

def build_graph(metric, start, end, probes, summary=True, zip_file=False):
    """Builds the graph for the probes, or a summary graph."""
    if metric == 'energy':
        return build_graph_energy_init(start, end, probes, summary, zip_file)
    else:
        return build_graph_network_init(start, end, probes, summary, zip_file)

def color_generator(nb_colors, hue=None):
    """Generates colors."""
    if not hue:
        hue=cfg.CONF.hue
    min_brightness = 50-nb_colors*15/2.0
    if min_brightness < 5:
        min_brightness = 5
    max_brightness = 50+nb_colors*15/2.0
    if max_brightness > 95:
        max_brightness = 95
    if nb_colors <= 1:
        min_brightness = 50
        step = 0
    else:
        step = (max_brightness-min_brightness) / (nb_colors-1.0)
    i = min_brightness
    while int(i) <= max_brightness:
        rgb = colorsys.hsv_to_rgb(hue/360.0,
                                  1,
                                  i/100.0)
        rgb = tuple([int(x*255) for x in rgb])
        yield '#' + struct.pack('BBB', *rgb).encode('hex')
        i += step
        if step == 0:
            break

def contains_multiprobes(probes, data_type='power'):
    for probe in probes:
        if(not find_multi_probe(probe, data_type) == probe):
            return True
    return False

def build_graph_energy_init(start, end, probes, summary, zip_file=False):
    """Builds the graph for the probes, or a summary graph."""
    # Graph is cachable ?
    cachable = False
    intervals = {}
    for scale in scales:
        intervals[scales[scale][0]['interval']] = {
            'resolution': scales[scale][0]['resolution'],
            'name': scale
        }
    scale = None
    if end - start in intervals:
        scale = intervals[end - start]['name']
        if end >= int(time.time()) - scales[scale][0]['resolution']:
            cachable = True

    if not isinstance(probes, list):
        probes = [probes]
    # Retrieve probes (and multi-probes)
    if len(probes) == 0:
        probes = list(probes_set_power)
    if not isinstance(probes, list):
        probes = [probes]
    probes = filter(lambda p: p in probes_set_power, probes)
    multi_probes_selected = set()
    for probe in probes:
        multi_probes_selected = multi_probes_selected.union(find_multi_probe(probe, 'power'))
    probes_uid = list(multi_probes_selected)

    # Single probe and no summary
    if len(probes) == 1 and not summary and scale:
        png_file = get_png_filename(probes[0], "power", scale)
    # All probes summary
    elif len(probes) == len(probes_set_power) and summary:
        png_file = cfg.CONF.png_dir + '/' + scale + '/summary-energy.png'
    # Other combinaison
    else:
        png_file = NamedTemporaryFile(prefix="kwapi", suffix=".png").name
    if zip_file:
         #Force temporary name
         png_file = NamedTemporaryFile(prefix="kwapi", suffix=".png").name

    # Get the file from cache
    if cachable and os.path.exists(png_file) and os.path.getmtime(png_file) > \
            time.time() - scales[scale][0]['resolution']:
        return png_file
    else:
        return build_graph_energy(start, end, probes_uid, probes, summary, cachable, png_file, scale)

def build_graph_energy(start, end, probes, probes_name, summary, cachable, png_file, scale):
    # Build required (PNG file not found or outdated)
    scale_label = ''
    if scale:
        scale_label = ' (' + scales[scale][0]['label'] + ')'
    if summary:
        # Specific arguments for summary graph
        args = [png_file,
                '--title', 'Summary' + scale_label,
                '--width', '694',
                '--height', '261',
                ]
    else:
        # Specific arguments for probe graph
        args = [png_file,
                '--title', str(",".join(probes_name)) + scale_label,
                '--width', '497',
                '--height', '187',
                '--upper-limit', str(cfg.CONF.max_metrics),
                ]
    # Common arguments
    args += ['--start', str(start),
             '--end', str(end),
             '--full-size-mode',
             '--imgformat', 'PNG',
             '--alt-y-grid',
             '--vertical-label', 'Watts',
             '--lower-limit', '0',
             '--rigid',
             ]
    if end - start <= 300:
        args += ['--x-grid', 'SECOND:30:MINUTE:1:MINUTE:1:0:%H:%M']
    cdef_watt = 'CDEF:watt='
    cdef_watt_with_unknown = 'CDEF:watt_with_unknown='
    graph_lines = []
    stack = False
    probe_list = sorted(probes, reverse=True)
    # Generate colors
    color_seq_green = color_generator(len(probe_list)+1)
    for probe in probe_list:
        probe_colors[probe] = color_seq_green.next()

    for probe in probe_list:
        probe_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, str(probe))
        rrd_file = get_rrd_filename(probe, "power")
        # Data source
        args.append('DEF:watt_with_unknown_%s=%s:w:AVERAGE'
                    % (probe_uuid, rrd_file))
        # Data source without unknown values
        args.append('CDEF:watt_%s=watt_with_unknown_%s,UN,0,watt_with_'
                    'unknown_%s,IF'
                    % (probe_uuid, probe_uuid, probe_uuid))
        # Prepare CDEF expression of total watt consumption
        cdef_watt += 'watt_%s,' % probe_uuid
        cdef_watt_with_unknown += 'watt_with_unknown_%s,' % probe_uuid
        # Draw the area for the probe
        color = probe_colors[probe]
        args.append('AREA:watt_with_unknown_%s%s::STACK'
                    % (probe_uuid, color + 'AA'))
        if not stack:
            graph_lines.append('LINE:watt_with_unknown_%s%s::'
                               % (probe_uuid, color))
            stack = True
        else:
            graph_lines.append('LINE:watt_with_unknown_%s%s::STACK'
                               % (probe_uuid, color))
    if len(probe_list) >= 2:
        # Prepare CDEF expression by adding the required number of '+'
        cdef_watt += '+,' * int(len(probe_list)-2) + '+'
        cdef_watt_with_unknown += '+,' * int(len(probe_list)-2) + '+'
    args += graph_lines
    args.append(cdef_watt)
    args.append(cdef_watt_with_unknown)
    # Min watt
    args.append('VDEF:wattmin=watt_with_unknown,MINIMUM')
    # Max watt
    args.append('VDEF:wattmax=watt_with_unknown,MAXIMUM')
    # Partial average that will be displayed (ignoring unknown values)
    args.append('VDEF:wattavg_with_unknown=watt_with_unknown,AVERAGE')
    # Real average (to compute kWh)
    args.append('VDEF:wattavg=watt,AVERAGE')
    # Compute kWh for the probe
    # RPN expressions must contain DEF or CDEF variables, so we pop a
    # CDEF value
    args.append('CDEF:kwh=watt,POP,wattavg,1000.0,/,%s,3600.0,/,*'
                % str(end - start))
    # Compute cost
    args.append('CDEF:cost=watt,POP,kwh,%f,*' % cfg.CONF.kwh_price)
    # Legend
    args.append('GPRINT:wattavg_with_unknown:Avg\: %3.1lf W')
    args.append('GPRINT:wattmin:Min\: %3.1lf W')
    args.append('GPRINT:wattmax:Max\: %3.1lf W')
    args.append('GPRINT:watt_with_unknown:LAST:Last\: %3.1lf W\j')
    args.append('TEXTALIGN:center')
    args.append('GPRINT:kwh:LAST:Total\: %lf kWh')
    args.append('GPRINT:cost:LAST:Cost\: %lf ' + cfg.CONF.currency)
    try:
        rrdtool.graph(args)
    except Exception as e:
        LOG.error("start %s, end %s, probes %s, probes_name %s, summary %s, cachable %s, png_file %s, scale %s" \
                  % (start, end, probes, probes_name, summary, cachable, png_file, scale))
        LOG.error("%s", e)
    return png_file


def build_graph_network_init(start, end, probes, summary, zip_file=False):
    """Builds the graph for the probes, or a summary graph."""
    # Graph is cachable ?
    cachable = False
    intervals = {}
    for scale in scales:
        intervals[scales[scale][0]['interval']] = {
            'resolution': scales[scale][0]['resolution'],
            'name': scale
        }
    scale = None
    if end - start in intervals:
        scale = intervals[end - start]['name']
        if end >= int(time.time()) - scales[scale][0]['resolution']:
            cachable = True

    # Retrieve probes (and multi-probes)
    if not isinstance(probes, list):
        probes = [probes]
    if len(probes) == 0:
        probes = list(probes_set_network)
    if not isinstance(probes, list):
        probes = [probes]
    probes = filter(lambda p: p in probes_set_network, probes)
    probes_in = set()
    probes_out = set()
    for probe in probes:
        for probe in find_probe_uid('network', probe):
           if get_rrd_filename(probe, "network_in") and get_rrd_filename(probe, "network_out"):
                probes_in.add(probe)
                probes_out.add(probe)
    probes_in = list(probes_in)
    probes_out = list(probes_out)

    # Single probe and no summary
    if len(probes) == 1 and not summary and scale:
        png_file = get_png_filename(probes[0], "network_in", scale)
    # All probes summary
    elif len(probes) == len(probes_set_network) and summary:
        png_file = cfg.CONF.png_dir + '/' + scale + '/summary-network.png'
    # Other combinaison
    else:
        png_file = NamedTemporaryFile(prefix="kwapi", suffix=".png").name
    if zip_file:
         #Force temporary name
         png_file = NamedTemporaryFile(prefix="kwapi", suffix=".png").name

    # Get the file from cache
    if cachable and os.path.exists(png_file) and os.path.getmtime(png_file) > \
            time.time() - scales[scale][0]['resolution']:
        return png_file
    else:
        return build_graph_network(start, end, probes, probes_in, probes_out, summary, cachable, png_file, scale)

def build_graph_network(start, end, probes, probes_in, probes_out, summary, cachable, png_file, scale):
    # Build required (PNG file not found or outdated)
    scale_label = ''
    if scale:
        scale_label = ' (' + scales[scale][0]['label'] + ')'
    if summary:
        # Specific arguments for summary graph
        args = [png_file,
                '--title', 'Summary' + scale_label,
                '--width', '694',
                '--height', '261',
                ]
    else:
        # Specific arguments for probe graph
        args = [png_file,
                '--title', str(probes[0]) + scale_label,
                '--width', '497',
                '--height', '187',
                #'--upper-limit', str(cfg.CONF.max_metrics),
                ]
    # Common arguments
    args += ['--start', str(start),
             '--end', str(end),
             '--full-size-mode',
             '--imgformat', 'PNG',
             '--alt-y-grid',
             '--vertical-label', 'bits/s',
             #'--lower-limit', '0',
             #'--rigid',
             '--base', '1000',
             ]
    if end - start <= 300:
        args += ['--x-grid', 'SECOND:30:MINUTE:1:MINUTE:1:0:%H:%M']
    cdef_metric_in = 'CDEF:metric_in='
    cdef_metric_with_unknown_in = 'CDEF:metric_with_unknown_in='
    cdef_metric_out = 'CDEF:metric_out='
    cdef_metric_with_unknown_out = 'CDEF:metric_with_unknown_out='
    graph_lines_in = []
    graph_lines_out = []
    stack_in = False
    stack_out = False
    probe_list = list(probes_in)
    # Generate colors
    color_seq_green = color_generator(len(probes_in)+1)
    for probe in sorted(probes_in, reverse=True):
        probe_colors[probe] = color_seq_green.next()

    #IN
    for probe in sorted(probe_list, reverse=True):
        probe_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, str(probe))
        rrd_file_in = get_rrd_filename(probe, "network_in")
        # Data source
        args.append('DEF:metric_with_unknown_%s_in=%s:o:AVERAGE'
            % (probe_uuid, rrd_file_in))
        args.append('CDEF:metric_with_unknown_%s_in_scale=metric_with_'
                    'unknown_%s_in,8,*,' % (probe_uuid,probe_uuid))
        # Data source without unknown values
        args.append('CDEF:metric_%s_in=metric_with_unknown_%s_in,UN,0,'
                    'metric_with_unknown_%s_in,8,*,IF,'
            % (probe_uuid, probe_uuid, probe_uuid))
        # Prepare CDEF expression of total metric in
        cdef_metric_in += 'metric_%s_in,8,*,' % probe_uuid
        cdef_metric_with_unknown_in += 'metric_with_unknown_%s_in,8,*,' \
                                       % probe_uuid
        # Draw the area for the probe in
        color = probe_colors.get(str(probe), '#336600')
        if not stack_in:
            args.append('AREA:metric_with_unknown_%s_in_scale%s::'
                % (probe_uuid, color + 'AA'))
            stack_in = True
        else:
            graph_lines_in.append('STACK:metric_with_unknown_%s_in_scale%s::'
                    % (probe_uuid, color + 'AA'))
    args += graph_lines_in

    # Generate colors
    color_seq_blue = color_generator(len(probes_out)+1, 190)
    for probe in sorted(probes_out, reverse=True):
        probe_colors[probe] = color_seq_blue.next()

    #OUT
    probe_list = list(probes_out)
    for probe in sorted(probe_list, reverse=True):
        probe_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, str(probe))
        rrd_file_out = get_rrd_filename(probe, "network_out")
        if not rrd_file_out:
            break
        # Data source
        args.append('DEF:metric_with_unknown_%s_out=%s:o:AVERAGE'
            % (probe_uuid, rrd_file_out))
        args.append('CDEF:metric_with_unknown_%s_out_neg=metric_with_'
                    'unknown_%s_out,-8,*,' % (probe_uuid,probe_uuid))
        # Data source without unknown values
        args.append('CDEF:metric_%s_out=metric_with_unknown_%s_out,UN,0,'
                    'metric_with_unknown_%s_out,8,*,IF,'
            % (probe_uuid, probe_uuid, probe_uuid))
        # Prepare CDEF expression of total metric out
        cdef_metric_out += 'metric_%s_out,8,*,' % probe_uuid
        cdef_metric_with_unknown_out += 'metric_with_unknown_%s_out,8,*,' \
                                        % probe_uuid
        #Draw the probe out
        color = probe_colors.get(str(probe),'#0033CC')
        if not stack_out:
            args.append('AREA:metric_with_unknown_%s_out_neg%s::'
                % (probe_uuid, color + 'AA'))
            stack_out = True
        else:
            graph_lines_out.append('STACK:metric_with_unknown_%s_out_neg%s::'
                    % (probe_uuid, color + 'AA'))
    args += graph_lines_out
    if len(probe_list) >= 2:
        # Prepare CDEF expression by adding the required number of '+'
        cdef_metric_in += '+,' * int(len(probes_in)-2) + '+'
        cdef_metric_with_unknown_in += '+,' * int(len(probes_in)-2) + '+'
        cdef_metric_out += '+,' * int(len(probes_out)-2) + '+'
        cdef_metric_with_unknown_out += '+,' * int(len(probes_out)-2) + '+'
    args.append('HRULE:0#000000')
    args.append(cdef_metric_in)
    args.append(cdef_metric_out)
    args.append(cdef_metric_with_unknown_in)
    args.append(cdef_metric_with_unknown_out)
    # IN
    # Min metric
    args.append('VDEF:metricmin_in=metric_with_unknown_in,MINIMUM')
    # Max metric
    args.append('VDEF:metricmax_in=metric_with_unknown_in,MAXIMUM')
    # Partial average that will be displayed (ignoring unknown values)
    args.append('VDEF:metricavg_with_unknown_in=metric_with_unknown_in,AVERAGE')
    # Real average
    args.append('VDEF:metricavg_in=metric_in,AVERAGE')
    # OUT
    # Min metric
    args.append('VDEF:metricmin_out=metric_with_unknown_out,MINIMUM')
    # Max metric
    args.append('VDEF:metricmax_out=metric_with_unknown_out,MAXIMUM')
    # Partial average that will be displayed (ignoring unknown values)
    args.append('VDEF:metricavg_with_unknown_out=metric_with_unknown_out,AVERAGE')
    # Real average
    args.append('VDEF:metricavg_out=metric_out,AVERAGE')
    # Legend
    args.append('GPRINT:metricavg_with_unknown_in:AvgIN\: %3.1lf%sb/s')
    args.append('GPRINT:metricmin_in:MinIN\: %3.1lf%sb/s')
    args.append('GPRINT:metricmax_in:MaxIN\: %3.1lf%sb/s')
    args.append('GPRINT:metric_with_unknown_in:LAST:LastIN\: %3.1lf%sb/s\j')
    args.append('GPRINT:metricavg_with_unknown_out:AvgOUT\: %3.1lf%sb/s')
    args.append('GPRINT:metricmin_out:MinOUT\: %3.1lf%sb/s')
    args.append('GPRINT:metricmax_out:MaxOUT\: %3.1lf%sb/s')
    args.append('GPRINT:metric_with_unknown_out:LAST:LastOUT\: %3.1lf%sb/s\j')
    args.append('TEXTALIGN:center')
    if len(probes_in) == 0 or len(probes_out) == 0:
        return None
    try:
        rrdtool.graph(args)
    except Exception as e:
        LOG.error("start %s, end %s, probes %s, probes_in %s, probes_out %s, summary %s, cachable %s, png_file %s, scale %s" \
                  % (start, end, probes, probes_in, probes_out, summary, cachable, png_file, scale))
        LOG.error("%s", e)
    return png_file
