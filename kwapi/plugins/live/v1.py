# -*- coding: utf-8 -*-
#
# Author: François Rossigneux <francois.rossigneux@inria.fr>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""This blueprint defines all URLs and answers."""

import flask
from jinja2 import TemplateNotFound


blueprint = flask.Blueprint('v1', __name__, static_folder='static')


@blueprint.route('/')
def welcome_live():
    try:
        return flask.render_template('index.html',
                                     view='all')
    except TemplateNotFound:
        flask.abort(404)


@blueprint.route('/<probe>/')
def welcome_probe(probe):
    try:
        return flask.render_template('index.html',
                                     probe=probe,
                                     view='probe')
    except TemplateNotFound:
        flask.abort(404)
