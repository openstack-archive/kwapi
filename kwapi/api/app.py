# -*- coding: utf-8 -*-

"""Set up the API server application instance."""

import logging

import flask
import flask.helpers

from kwapi import config
from collector import Collector
import v1
#import acl

def make_app(enable_acl=True):
    """Instantiates Flask app, attaches collector database, installs acl."""
    logging.info('Starting API')
    app = flask.Flask('kwapi.api')
    app.register_blueprint(v1.blueprint, url_prefix='/v1')
    
    collector = Collector(config.CONF['collector_socket'])
    collector.clean(config.CONF['collector_cleaning_interval'], periodic=True)
    
    @app.before_request
    def attach_config():
        flask.request.database = collector.database
    
    # Install the middleware wrapper
    if enable_acl:
        return acl.install(app, cfg.CONF)
    
    return app
