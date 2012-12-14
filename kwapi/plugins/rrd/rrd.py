# -*- coding: utf-8 -*-

"""Defines functions to build and update rrd database and graph."""

import collections
import errno
import itertools
import json
import os
import time
import threading
import uuid

import rrdtool
import zmq

from kwapi.openstack.common import cfg, log
from kwapi import security

LOG = log.getLogger(__name__)

rrd_opts = [
    cfg.BoolOpt('signature_checking',
               required=True,
               ),
    cfg.FloatOpt('kwh_price',
                 required=True,
                 ),
    cfg.IntOpt('max_watts',
               required=True,
               ),
    cfg.MultiStrOpt('probes_endpoint',
                    required=True,
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

cfg.CONF.register_opts(rrd_opts)

scales = collections.OrderedDict()
scales['minute'] = {'interval':300, 'resolution':1, 'label': '5 minutes'},    # Resolution = 1 second
scales['hour'] = {'interval':3600, 'resolution':10, 'label': 'hour'},         # Resolution = 10 seconds
scales['day'] = {'interval':86400, 'resolution':900, 'label': 'day'},         # Resolution = 15 minutes
scales['week'] = {'interval':604800, 'resolution':7200, 'label': 'week'},     # Resolution = 2 hours
scales['month'] = {'interval':2678400, 'resolution':21600, 'label': 'month'}, # Resolution = 6 hours
scales['year'] = {'interval':31622400, 'resolution':604800, 'label': 'year'}, # Resolution = 1 week
    
probes = set()

def create_dirs():
    """Creates all required directories."""
    directories = []
    directories.append(cfg.CONF.png_dir)
    directories.append(cfg.CONF.rrd_dir)
    # Build a list of directory names
    # Avoid loop in try block (problem if exception occurs), and avoid multiple try blocks (too long)
    for scale in scales.keys():
        directories.append(cfg.CONF.png_dir + '/' + scale)
    # Create each directory in a try block, and continue if directory already exist
    for directory in directories:
        try:
            os.makedirs(directory)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

def get_png_filename(scale, probe):
    """Returns the png filename."""
    return cfg.CONF.png_dir + '/' + scale + '/' + str(uuid.uuid5(uuid.NAMESPACE_DNS, str(probe))) + '.png'

def get_rrd_filename(probe):
    """Returns the rrd filename."""
    return cfg.CONF.rrd_dir + '/' + str(uuid.uuid5(uuid.NAMESPACE_DNS, str(probe))) + '.rrd'

def create_rrd_file(filename):
    """Creates a RRD file."""
    if not os.path.exists(filename):
        args = [filename,
                '--start', '0',
                '--step', '1',
                # Heartbeat = 600 seconds, Min = 0, Max = Unlimited
                'DS:w:GAUGE:600:0:U',
                ]
        for scale in scales.keys():
            args.append('RRA:AVERAGE:0.5:%s:%s' % (scales[scale][0]['resolution'], scales[scale][0]['interval']/scales[scale][0]['resolution']))
            rrdtool.create(args)

def update_rrd(probe, watts):
    """Updates RRD file associated with this probe."""
    filename = cfg.CONF.rrd_dir + '/' + str(uuid.uuid5(uuid.NAMESPACE_DNS, str(probe))) + '.rrd'
    if not os.path.isfile(filename):
        create_rrd_file(filename)
    probes.add(probe)
    try:
        rrdtool.update(filename, 'N:%s' % watts)
    except rrdtool.error, e:
        LOG.error('Error updating RRD: %s' % e)

def build_summary_graph(scale):
    """Builds the summary graph."""
    png_file = cfg.CONF.png_dir + '/' + scale + '/summary.png'
    
    if scale in scales.keys() and len(probes) > 0:
        # Build required (PNG file not found or outdated)
        if not os.path.exists(png_file) or os.path.getmtime(png_file) < time.time() - scales[scale][0]['resolution']:
            args = [png_file,
                    '--start', '-' + str(scales[scale][0]['interval']),
                    '--end', 'now',
                    '--width', '694',
                    '--height', '261',
                    '--full-size-mode',
                    '--imgformat', 'PNG',
                    '--title', 'Summary (' + scales[scale][0]['label'] + ')',
                    '--vertical-label', 'Watts',
                    '--lower-limit', '0',
                    '--rigid',
                    ]
            # Colors of the areas in the graph
            colors = ['#EA644A', '#EC9D48', '#ECD748', '#54EC48', '#48C4EC', '#DE48EC', '#7648EC']
            seq = itertools.cycle(colors)
            
            cdef_kwh = 'CDEF:kwh='
            cdef_cost = 'CDEF:cost='
            for probe in probes:
                rrd_file = get_rrd_filename(probe)
                if os.path.exists(rrd_file):
                    # Data source
                    args.append('DEF:watt_with_unknown_%s=%s:w:AVERAGE' % (probe, rrd_file))
                    # Data source with unknown values set to zero
                    args.append('CDEF:watt_%s=watt_with_unknown_%s,UN,0,watt_with_unknown_%s,IF' % (probe, probe, probe))
                    # Real average (to compute kWh)
                    args.append('VDEF:wattavg_%s=watt_%s,AVERAGE' % (probe, probe))
                    # Compute kWh for the probe
                    # RPN expressions must contain DEF or CDEF variables, so we pop a CDEF value
                    args.append('CDEF:kwh_%s=watt_%s,POP,wattavg_%s,1000.0,/,%s,3600.0,/,*' % (probe, probe, probe, str(scales[scale][0]['interval'])))
                    # Compute cost
                    args.append('CDEF:cost_%s=kwh_%s,%f,*' % (probe, probe, cfg.CONF.kwh_price))
                    # Append kWh and cost to a CDEF expression
                    cdef_kwh += 'kwh_' + probe + ','
                    cdef_cost += 'cost_' + probe + ','
                    # Draw the area for the probe
                    args.append('AREA:watt_%s%s::STACK' % (probe, seq.next()))
            # Prepare CDEF expression of kWh and cost by adding the required number of '+'
            cdef_kwh += '+,' * int(len(probes)-2) + '+'
            cdef_cost += '+,' * int(len(probes)-2) + '+'
            # Distinguish the quantity of probes because CDEF expression is invalid if there is less than 2 probes
            if len(probes) >= 2:
                args.append(cdef_kwh)
                args.append(cdef_cost)
                # Legend
                args.append('GPRINT:kwh:LAST:Total\: %lf kWh')
                args.append('GPRINT:cost:LAST:Cost\: %lf €')
            else:
                # Legend
                args.append('GPRINT:kwh_%s' % list(probes)[0] + ':LAST:Total\: %lf kWh')
                args.append('GPRINT:cost_%s' % list(probes)[0] + ':LAST:Cost\: %lf €')
            LOG.info('Build PNG summary graph')
            rrdtool.graph(args)
            return png_file
        else:
            LOG.info('Retrieve PNG summary graph from cache')
            return png_file

def build_graph(scale, probe):
    """Builds the graph for this probe."""
    png_file = get_png_filename(scale, probe)
    rrd_file = get_rrd_filename(probe)
    
    if scale in scales.keys() and os.path.exists(rrd_file):
        # Build required (PNG file not found or outdated)
        if not os.path.exists(png_file) or os.path.getmtime(png_file) < time.time() - scales[scale][0]['resolution']:
            LOG.info('Build PNG graph')
            rrdtool.graph(png_file,
                          '--start', '-' + str(scales[scale][0]['interval']),
                          '--end', 'now',
                          '--upper-limit', str(cfg.CONF.max_watts),
                          '--imgformat', 'PNG',
                          # Data source
                          'DEF:watt_with_unknown=%s:w:AVERAGE' % rrd_file,
                          # Min watt
                          'VDEF:wattmin=watt_with_unknown,MINIMUM',
                          # Max watt
                          'VDEF:wattmax=watt_with_unknown,MAXIMUM',
                          # Data source with unknown values set to zero
                          'CDEF:watt=watt_with_unknown,UN,0,watt_with_unknown,IF',
                          # Partial average that will be displayed (ignoring unknown values)
                          'VDEF:wattavg_with_unknown=watt_with_unknown,AVERAGE',
                          # Real average (to compute kWh)
                          'VDEF:wattavg=watt,AVERAGE',
                          # Compute kWh for the probe
                          # RPN expressions must contain DEF or CDEF variables, so we pop a CDEF value
                          'CDEF:kwh=watt,POP,wattavg,1000.0,/,%s,3600.0,/,*' % str(scales[scale][0]['interval']),
                          # Compute cost
                          'CDEF:cost=watt,POP,kwh,%f,*' % cfg.CONF.kwh_price,
                          '--title', probe + ' (' + scales[scale][0]['label'] + ')',
                          '--vertical-label', 'Watts',
                          '--lower-limit', '0',
                          '--rigid',
                          # Draw the area and a line for the probe
                          'AREA:watt_with_unknown#0000FF22',
                          'LINE:watt_with_unknown#0000FFAA',
                          # Legend
                          'GPRINT:wattavg_with_unknown:Avg\: %3.1lf W',
                          'GPRINT:wattmin:Min\: %3.1lf W',
                          'GPRINT:wattmax:Max\: %3.1lf W',
                          'GPRINT:watt_with_unknown:LAST:Last\: %3.1lf W',
                          'GPRINT:kwh:LAST:Total\: %lf kWh',
                          'GPRINT:cost:LAST:Cost\: %lf €',
                          )
        else:
            LOG.info('Retrieve PNG graph from cache')
        return png_file
    else:
        LOG.warning('Probe or scale not found')

def listen():
    """Subscribes to ZeroMQ messages, and adds received measurements to the database.
    Messages are dictionaries dumped in JSON format.
    
    """
    LOG.info('RRD listenig to %s' % cfg.CONF.probes_endpoint)
    
    context = zmq.Context.instance()
    subscriber = context.socket(zmq.SUB)
    subscriber.setsockopt(zmq.SUBSCRIBE, '')
    for endpoint in cfg.CONF.probes_endpoint:
        subscriber.connect(endpoint)
    
    while True:
        message = subscriber.recv()
        measurements = json.loads(message)
        if not isinstance(measurements, dict):
            LOG.error('Bad message type (not a dict)')
        elif cfg.CONF.signature_checking and not security.verify_signature(measurements, cfg.CONF.driver_metering_secret):
            LOG.error('Bad message signature')
        else:
            try:
                update_rrd(measurements['probe_id'].encode('utf-8'), float(measurements['w']))
            except KeyError:
                LOG.error('Malformed message (missing required key)')
