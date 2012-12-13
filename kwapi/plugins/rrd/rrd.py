# -*- coding: utf-8 -*-

"""Define functions to build and update rrd database and graph."""

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
    cfg.IntOpt('rebuild_graphs_interval',
                required=True,
                ),
    cfg.MultiStrOpt('probes_endpoint',
                    required=True,
                    ),
    cfg.StrOpt('driver_metering_secret',
               required=False,
               ),
    cfg.StrOpt('rrd_dir',
               required=True,
               ),
    ]

cfg.CONF.register_opts(rrd_opts)

rrd_files = {}

def create_rrd_file(filename):
    """Creates a RRD file."""
    if not os.path.isdir(cfg.CONF.rrd_dir):
        try:
            os.makedirs(cfg.CONF.rrd_dir)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise
    if not os.path.exists(filename):
        rrdtool.create(filename,
                       '--step', '60',
                       '--start', '0',
                       'DS:watt:GAUGE:600:0:U',
                       'RRA:AVERAGE:0.5:1:60',
                       )

def update_rrd_file(probe, watt):
    """Updates the RRD file. Filename is based on probe name."""
    filename = cfg.CONF.rrd_dir + '/' + str(uuid.uuid5(uuid.NAMESPACE_DNS, str(probe))) + '.rrd'
    if filename in rrd_files.values():
        updatestr = str(u'%s:%s' % (time.time(), watt ))
        try:
            ret = rrdtool.update(filename, updatestr)
        except rrdtool.error, e:
            LOG.error('Error updating RRD: %s' % e)
    else:
        create_rrd_file(filename)
        rrd_files[probe] = filename

def build_rrd_graphs():
    """Builds PNG graphs from RRD files.
    If periodic, this method is executed automatically after the timeout interval.
    
    """
    LOG.info('Build PNG graphs from RRD files')
    for probe, rrd_file in rrd_files.iteritems():
        png_file = os.path.dirname(rrd_file) + '/' + os.path.basename(rrd_file).replace('.rrd', '.png')
        rrdtool.graph(png_file,
                      '--start', '-%i' % 3600,
                      '--end', 'now',
                      '--imgformat', 'PNG',
                      'DEF:watt=%s:watt:AVERAGE' % rrd_file,
                      '--title', "Last hour",
                      '--vertical-label', 'Watts',
                      '--lower-limit', '0',
                      '--rigid',
                      'AREA:watt#0000FF22:' + str(probe),
                      'LINE:watt#0000FFAA:',
                      'GPRINT:watt:LAST:Last measure\: %3.1lf W')
    
    if cfg.CONF.rebuild_graphs_interval > 0:
        timer = threading.Timer(cfg.CONF.rebuild_graphs_interval, build_rrd_graphs)
        timer.daemon = True
        timer.start()
    
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
                update_rrd_file(measurements['probe_id'], float(measurements['w']))
            except KeyError:
                LOG.error('Malformed message (missing required key)')
