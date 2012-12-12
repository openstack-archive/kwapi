# -*- coding: utf-8 -*-

"""Set up the RRD server application instance."""

import thread

import flask

from kwapi.openstack.common import cfg, log
#from collector import Collector
import rrd
import v1

LOG = log.getLogger(__name__)

app_opts = [
    cfg.FloatOpt('kwh_price',
                 required=False,
                 ),
    ]

cfg.CONF.register_opts(app_opts)

def make_app():
    """Instantiates Flask app, attaches collector database. """
    LOG.info('Starting RRD')
    app = flask.Flask(__name__)
    app.register_blueprint(v1.blueprint)
    
    thread.start_new_thread(rrd.listen, ())
    thread.start_new_thread(rrd.build_rrd_graphs, ())
    
    @app.before_request
    def attach_config():
        flask.request.rrd_files = rrd.rrd_files
    return app
