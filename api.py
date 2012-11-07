#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, redirect, url_for, jsonify, abort
import collector

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
    if not probe in database:
        abort(404)
    result = {probe: database[probe]}
    return jsonify(result)

@app.route('/v1/probes/<probe>/<meter>/')
def v1_probe_value(probe, meter):
    if not probe in database or not meter in database[probe]._asdict():
        abort(404)
    result = {meter: database[probe]._asdict()[meter]}
    return jsonify(result)

if __name__ == '__main__':
    collector = collector.Collector()
    collector.clean(3600*24, True)
    collector.start_listen()
    database = collector.database
    app.run(debug=True)
