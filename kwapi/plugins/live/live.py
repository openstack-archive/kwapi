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
# License for the specific language governing permissions and limitations
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

import rrdtool

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
    cfg.IntOpt('max_watts',
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

# Probe set uid
probes_uid_set_network = nx.Graph()
probes_uid_set_power = nx.Graph()

# Loads topology from config file.
parser = cfg.ConfigParser('/etc/kwapi/live.conf', {})
parser.parse()
site = getfqdn().split('.')[1]

for section, entries in parser.sections.iteritems():
    if section == 'TOPO':
        powerProbes = set(ast.literal_eval(entries['powerProbes'][0]))
        for powerProbe in powerProbes:
            site, probe = powerProbe.split('.')
            cluster = probe.split('-')[0]
            for number in probe.split('-')[1:]:
                probes_uid_set_power.add_node(powerProbe, rrd=True)
                probes_uid_set_power.add_edge(site + '.' + cluster + '-' + number, powerProbe)

all_uid_power = [n[0] for n in probes_uid_set_power.nodes(True) \
             if n[1].get('rrd', False)]

node_to_remove = set()

probe_colors = {}
lock = Lock()

def find_multi_probe(probe):
    """Input: nancy.griffon-1"""
    """Output: nancy.giffon-1-2-3...-x"""
    try:
        return probes_uid_set_power.neighbors(probe)[0]
    except:
        return None


def find_probe_uid(metric, probe_name):
    if metric == 'power':
        #if not probe_name in probes_uid_set_power:
        #    return None
        probe_uid = find_multi_probe(probe_name)
        return probe_uid
    if metric == 'network':
        #if not probe_name in probes_set_network:
        #    return None
        # Return (probe_uid in, probe_uid out)
        switch_or_probes = []
        try:
            res = probes_uid_set_network.neighbors(probe_name)
        except:
            res = []
        res2 = []
        for p in res:
            res2.append((probe_name + '_' + str(p).split('.')[1],\
                    str(p) + '_' + probe_name.split('.')[1]))
        return res2

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


def get_png_filename(scale, probe):
    """Returns the png filename."""

    return cfg.CONF.png_dir + '/' + scale + '/' + \
        str(uuid.uuid5(uuid.NAMESPACE_DNS, str(probe))) + '.png'


def get_rrd_filename(probe):
    """Returns the rrd filename."""
    # Include params in the path
    filename = cfg.CONF.rrd_dir + '/' + str(uuid.uuid5(uuid.NAMESPACE_DNS,
                                        str(probe))) + '.rrd'
    if os.path.exists(filename):
        return filename
    else:
        LOG.error("No file for %s." % probe)
        return None

def update_probe(probe, data_type, timestamp, metrics, params):
    if data_type == 'power':
        site, probeP = probe.split('.')
        cluster = probeP.split('-')[0]
        for number in probeP.split('-')[1:]:
            probes_uid_set_power.add_edge('.'.join([site, cluster, number]),\
                    probeP)
            probes_set_power.add('.'.join([site, cluster]) + "-" +number)
    if 'network' in data_type:
        site, probeP = probe.split('.')
        src, dest = probeP.split('_')
        probes_uid_set_network.add_edge('.'.join([site, src]), '.'.join([site, dest]))
        new_node = site + '.' + src
        probes_set_network.add(new_node)
        new_node = site + '.' + dest
        probes_set_network.add(new_node)


def build_graph(metric, start, end, probes, summary=True):
    """Builds the graph for the probes, or a summary graph."""
    if metric == 'energy':
        return build_graph_energy_init(start, end, probes, summary)
    else:
        return build_graph_network_init(start, end, probes, summary)

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

def contains_multiprobes(probes):
    for probe in probes:
        if(not find_multi_probe(probe) == probe):
            LOG.info("Contain multiprobe")
            return True
    LOG.info("Contain no multiprobe") 
    return False

def build_graph_energy_init(start, end, probes, summary):
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
    multi_probes_selected = set()
    for probe in probes:
        multi_probes_selected.add(find_multi_probe(probe))
    probes = list(multi_probes_selected)
    probes = [probe for probe in probes if get_rrd_filename(probe)]
    # Only one probe
    if len(probes) == 1 and not summary and cachable:
        png_file = get_png_filename(scale, probes[0])
    # All probes
    elif not probes or len(probes) == len(all_uid_power) and cachable:
        png_file = cfg.CONF.png_dir + '/' + scale + '/summary-energy.png'
        probes = all_uid_power
    # Specific combinaison of probes
    else:
        png_file = '/tmp/' + str(uuid.uuid4()) + '.png'
    return build_graph_energy(start, end, probes, summary, cachable, png_file, scale)
    
def build_graph_energy(start, end, probes, summary, cachable, png_file, scale):
    # Get the file from cache
    if cachable and os.path.exists(png_file) and os.path.getmtime(png_file) > \
            time.time() - scales[scale][0]['resolution']:
        LOG.info('Retrieve PNG graph from cache %s' % png_file)
        return png_file
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
                '--upper-limit', str(cfg.CONF.max_watts),
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
    for probe in probe_list:
        probe_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, str(probe))
        rrd_file = get_rrd_filename(probe)
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
    LOG.info('Build PNG graph %s' % png_file)
    rrdtool.graph(args)
    return png_file


def build_graph_network_init(start, end, probes, summary):
    """Builds the graph for the probes, or a summary graph."""
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
    probes = [probe for probe in probes if probe in probes_set_network]
    probes_in = set() 
    probes_out = set()
    for probe in probes:
        for probe_in, probe_out in find_probe_uid('network', probe):
           if get_rrd_filename(probe_in) and get_rrd_filename(probe_out):
                probes_in.add(probe_in)
                probes_out.add(probe_out)
    probes_in = list(probes_in)
    probes_out = list(probes_out)
    # Only one probe
    if len(probes_in) == 1 and not summary and cachable:
        png_file = get_png_filename(scale, probes_in[0])
        if not png_file:
            return None
    # All probes
    elif not probes_in or len(probes_in) == len(probes_set_network) and cachable:
        png_file = cfg.CONF.png_dir + '/' + scale + '/summary-network.png'
        probes = list(probes_set_network)
    # Specific combinaison of probes
    else:
        png_file = '/tmp/' + str(uuid.uuid4()) + '.png'
    return build_graph_network(start, end, probes, probes_in, probes_out, summary, cachable, png_file, scale)
    
def build_graph_network(start, end, probes, probes_in, probes_out, summary, cachable, png_file, scale):
    # Get the file from cache
    if cachable and os.path.exists(png_file) and os.path.getmtime(png_file) > \
            time.time() - scales[scale][0]['resolution']:
        LOG.info('Retrieve PNG graph from cache')
        return png_file
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
        rrd_file_in = get_rrd_filename(probe)
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
        rrd_file_out = get_rrd_filename(probe)
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
    LOG.info('Build PNG graph')
    if len(probes_in) == 0 or len(probes_out) == 0:
        return None
    rrdtool.graph(args)
    return png_file
