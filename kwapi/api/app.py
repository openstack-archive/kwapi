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
    cfg.IntOpt('api_port',
                required=True,
                ),
    cfg.StrOpt('api_metering_secret',
               required=True,
               ),
    ]

cfg.CONF.register_opts(app_opts)

def make_app(conf):
    """Instantiates Flask app, attaches collector database, installs acl."""
    LOG.info('Starting API')
    app = flask.Flask('kwapi.api')
    app.register_blueprint(v1.blueprint, url_prefix='/v1')
    
    collector = Collector(cfg.CONF)
    collector.clean(cfg.CONF, periodic=True)
    
    @app.before_request
    def attach_config():
        flask.request.database = collector.database
    
    # Install the middleware wrapper
    if conf.acl_enabled:
        return acl.install(app)
    
    return app
