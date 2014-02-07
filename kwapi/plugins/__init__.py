

from kwapi.utils import cfg, log



def listen(function):
    """Subscribes to ZeroMQ messages, and adds received measurements to the
    database. Messages are dictionaries dumped in JSON format.

    """
    LOG.info('Listening to %s' % cfg.CONF.probes_endpoint)

    context = zmq.Context.instance()
    subscriber = context.socket(zmq.SUB)
    if not cfg.CONF.watch_probe:
        subscriber.setsockopt(zmq.SUBSCRIBE, '')
    else:
        for probe in cfg.CONF.watch_probe:
            subscriber.setsockopt(zmq.SUBSCRIBE, probe + '.')
    for endpoint in cfg.CONF.probes_endpoint:
        subscriber.connect(endpoint)

    while True:
        [probe, message] = subscriber.recv_multipart()
        measurements = json.loads(message)
        if not isinstance(measurements, dict):
            LOG.error('Bad message type (not a dict)')
        elif cfg.CONF.signature_checking and \
            not security.verify_signature(measurements,
                                          cfg.CONF.driver_metering_secret):
            LOG.error('Bad message signature')
        else:
            try:
                probe = measurements['probe_id'].encode('utf-8')
                function(probe, float(measurements['w']))
            except (TypeError, ValueError):
                LOG.error('Malformed power consumption data: %s'
                          % measurements['w'])
            except KeyError:
                LOG.error('Malformed message (missing required key)')

