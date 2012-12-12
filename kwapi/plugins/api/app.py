# -*- coding: utf-8 -*-

"""Set up the API server application instance."""

import flask

from kwapi.openstack.common import cfg, log
import acl
from collector import Collector
import v1

LOG = log.getLogger(__name__)

app_opts = [
    cfg.BoolOpt('acl_enabled',
                required=True,
                ),
    ]

cfg.CONF.register_opts(app_opts)

def make_app():
    """Instantiates Flask app, attaches collector database, installs acl."""
    LOG.info('Starting API')
    app = flask.Flask(__name__)
    app.register_blueprint(v1.blueprint, url_prefix='/v1')
    
    collector = Collector()
    collector.clean()
    
    @app.before_request
    def attach_config():
        flask.request.database = collector.database
    
    # Install the middleware wrapper
    if cfg.CONF.acl_enabled:
        return acl.install(app)
    
    return app
