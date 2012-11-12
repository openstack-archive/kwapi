#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, redirect, url_for, jsonify, abort
import collector
import config

app = Flask(__name__)

@app.route('/')
def index():
    return redirect(url_for('v1'))

@app.route('/v1/')
def v1():
    return 'Welcome to Kwapi!'

@app.route('/v1/probes/')
def v1_probe_list():
    return jsonify(probes=database.keys())

@app.route('/v1/probes/<probe>/')
def v1_probe_info(probe):
    try:
        result = {probe: database[probe]}
    except KeyError:
        abort(404)
    return jsonify(result)

@app.route('/v1/probes/<probe>/<meter>/')
def v1_probe_value(probe, meter):
    try:
        result = {meter: database[probe][meter]}
    except KeyError:
        abort(404)
    return jsonify(result)

if __name__ == '__main__':
    config = config.get_config('kwapi.conf', 'configspec.ini')
    if config is None:
        sys.exit(1)
    
    collector = collector.Collector()
    collector.clean(config['collector_cleaning_interval'], periodic=True)
    collector.start_listen(config['socket'])
    database = collector.database
    app.run(debug=True)
