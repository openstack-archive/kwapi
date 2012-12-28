# -*- coding: utf-8 -*-

"""Set up the RRD server application instance."""

import thread

import flask

from kwapi.openstack.common import log
import rrd
import v1

LOG = log.getLogger(__name__)

def make_app():
    """Instantiates Flask app, attaches collector database. """
    LOG.info('Starting RRD')
    app = flask.Flask(__name__)
    app.register_blueprint(v1.blueprint)
    
    thread.start_new_thread(rrd.listen, ())
    
    @app.before_request
    def attach_config():
        flask.request.probes = rrd.probes
        flask.request.scales = rrd.scales
    return app
