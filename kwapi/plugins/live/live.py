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

import rrdtool

from kwapi.utils import cfg, log

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
scales['minute'] = {'interval': 300, 'resolution': 1, 'label': '5 minutes'},
# Resolution = 10 seconds
scales['hour'] = {'interval': 3600, 'resolution': 10, 'label': 'hour'},
# Resolution = 15 minutes
scales['day'] = {'interval': 86400, 'resolution': 900, 'label': 'day'},
# Resolution = 2 hours
scales['week'] = {'interval': 604800, 'resolution': 7200, 'label': 'week'},
# Resolution = 6 hours
scales['month'] = {'interval': 2678400, 'resolution': 21600, 'label': 'month'},
# Resolution = 1 week
scales['year'] = {'interval': 31622400, 'resolution': 604800, 'label': 'year'},

probes_set = set()
topo_g5k = {}
"""Loads topology from config file."""
parser = cfg.ConfigParser('/etc/kwapi/live.conf', {})
parser.parse()
for section, entries in parser.sections.iteritems():
    if section == 'TOPO':
        topo_g5k = ast.literal_eval(entries['topo'][0])
        reverse = {}
        for k in topo_g5k.keys():
            for v in topo_g5k[k]:
                if not v in reverse:
                    reverse[v]=[]
                reverse[v].append(k)
        topo_g5k.update(reverse)

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


def get_png_filename(scale, probe):
    """Returns the png filename."""
    return cfg.CONF.png_dir + '/' + scale + '/' + \
        str(uuid.uuid5(uuid.NAMESPACE_DNS, str(probe))) + '.png'


def get_rrd_filename(probe):
    """Returns the rrd filename."""
    # Include params in the path
    return cfg.CONF.rrd_dir + '/' + str(uuid.uuid5(uuid.NAMESPACE_DNS,
                                        str(probe))) + '.rrd'

def update_probe(probe, data_type, timestamp, metrics, params):
    if not '_' in probe:
        if not probe in probes_set:
            color_seq = color_generator(len(probes_set)+1)
            lock.acquire()
            probes_set.add(probe)
            for probe in sorted(probes_set, reverse=True):
                probe_colors[probe] = color_seq.next()
            lock.release()

def build_graph(metric, start, end, probes, summary=True):
    """Builds the graph for the probes, or a summary graph."""
    if metric == 'energy':
        return build_graph_energy(start, end, probes, summary)
    else:
        return build_graph_network(start, end, probes, summary)

def color_generator(nb_colors):
    """Generates colors."""
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
        rgb = colorsys.hsv_to_rgb(cfg.CONF.hue/360.0,
                                  1,
                                  i/100.0)
        rgb = tuple([int(x*255) for x in rgb])
        yield '#' + struct.pack('BBB', *rgb).encode('hex')
        i += step
        if step == 0:
            break

def build_graph_energy(start, end, probes, summary):
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
    probes = [probe for probe in probes if probe in probes_set]
    if len(probes_set) == 0:
        return
    # Only one probe
    if len(probes) == 1 and not summary and cachable:
        png_file = get_png_filename(scale, probes[0])
    # All probes
    elif not probes or set(probes) == probes_set and cachable:
        png_file = cfg.CONF.png_dir + '/' + scale + '/summary-energy.png'
        probes = list(probes_set)
    # Specific combinaison of probes
    else:
        png_file = '/tmp/' + str(uuid.uuid4()) + '.png'
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
                '--title', probes[0] + scale_label,
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
        probe_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, probe)
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
    LOG.info('Build PNG graph')
    rrdtool.graph(args)
    return png_file

def build_graph_network(start, end, probes, summary):
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

    probes = [probe for probe in probes if probe in probes_set]
    probes_in = []
    probes_out = []
    for probe in sorted(probes, reverse=True):
        dest = topo_g5k[probe][0]
        site = probe.split('.')[0]
        probe_name = probe.split('.')[1]
        probes_in.append(probe + '_' + dest)
        probes_out.append(site + '.' + dest + '_' + probe_name)

    if len(probes_set) == 0:
        return
    # Only one probe
    if len(probes_in) == 1 and not summary and cachable:
        png_file = get_png_filename(scale, probes_in[0])
    # All probes
    elif not probes_in or len(set(probes_in)) == len(probes_set) and cachable:
        png_file = cfg.CONF.png_dir + '/' + scale + '/summary-network.png'
        #probes = list(probes_in)
    # Specific combinaison of probes
    else:
        png_file = '/tmp/' + str(uuid.uuid4()) + '.png'
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
                '--title', probes[0] + scale_label,
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
    probe_list = probes_in
    #IN
    for probe in probe_list:
        probe_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, probe)
        rrd_file_in = get_rrd_filename(probe)
        # Data source
        args.append('DEF:metric_with_unknown_%s_in=%s:o:AVERAGE'
            % (probe_uuid, rrd_file_in))
        # Data source without unknown values
        args.append('CDEF:metric_%s_in=metric_with_unknown_%s_in,UN,0,'
                    'metric_with_unknown_%s_in,IF'
            % (probe_uuid, probe_uuid, probe_uuid))
        # Prepare CDEF expression of total metric in
        cdef_metric_in += 'metric_%s_in,' % probe_uuid
        cdef_metric_with_unknown_in += 'metric_with_unknown_%s_in,' \
                                       % probe_uuid
        # Draw the area for the probe in
        color = '#336600'
        if not stack_in:
            args.append('AREA:metric_with_unknown_%s_in%s::'
                % (probe_uuid, color))
            stack_in = True
        else:
            graph_lines_in.append('STACK:metric_with_unknown_%s_in%s::'
                    % (probe_uuid, color))
    args += graph_lines_in
    #OUT
    probe_list = probes_out
    for probe in probe_list:
        probe_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, probe)
        rrd_file_out = get_rrd_filename(probe)
        # Data source
        args.append('DEF:metric_with_unknown_%s_out=%s:o:AVERAGE'
            % (probe_uuid, rrd_file_out))
        args.append('CDEF:metric_with_unknown_%s_out_neg=metric_with_'
                    'unknown_%s_out,-1,*' % (probe_uuid,probe_uuid))
        # Data source without unknown values
        args.append('CDEF:metric_%s_out=metric_with_unknown_%s_out,UN,0,'
                    'metric_with_unknown_%s_out,IF'
            % (probe_uuid, probe_uuid, probe_uuid))
        # Prepare CDEF expression of total metric out
        cdef_metric_out += 'metric_%s_out,' % probe_uuid
        cdef_metric_with_unknown_out += 'metric_with_unknown_%s_out,' \
                                        % probe_uuid
        #Draw the probe out
        color = '#0033CC'
        if not stack_out:
            args.append('AREA:metric_with_unknown_%s_out_neg%s::'
                % (probe_uuid, color))
            stack_out = True
        else:
            graph_lines_out.append('STACK:metric_with_unknown_%s_out_neg%s::'
                    % (probe_uuid, color))
    args += graph_lines_out
    if len(probe_list) >= 2:
        # Prepare CDEF expression by adding the required number of '+'
        cdef_metric_in += '+,' * int(len(probe_list)-2) + '+'
        cdef_metric_with_unknown_in += '+,' * int(len(probe_list)-2) + '+'
        cdef_metric_out += '+,' * int(len(probe_list)-2) + '+'
        cdef_metric_with_unknown_out += '+,' * int(len(probe_list)-2) + '+'
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
    rrdtool.graph(args)
    return png_file
