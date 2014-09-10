#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#
# Generates the DATA_TYPES dictionnary:
"""
DATA_TYPES = {
    'power': {
        'units': 'watts',
        'summable': True,
        'rrd': 'GAUGE:600:0:U',
        'parameters': {}
    },
    'ifOctets': {
        'units': 'bits/s',
        'summable': False,
        'rrd': 'COUNTER:600:0:4294967295',
        'parameters': {
	'flow': ['in', 'out'],
	'dest': str
        },
    },
    'ifHCOctets': {
        'units': 'bits/s',
        'summable': False,
        'rrd': 'DERIVE:600:0:U',
        'parameters': {
	'flow': ['in', 'out'],
	'dest': str
        }
    }
}
"""

import sys, ast

from kwapi.utils import cfg, log

LOG = log.getLogger(__name__)
parser = cfg.ConfigParser('/etc/kwapi/data_types.conf', {})
parser.parse()

DATA_TYPES = {}
MANDATORY_OPTIONS = []
for name, value in parser.sections['DEFAULT'].items():
    MANDATORY_OPTIONS.extend(ast.literal_eval(value[0]))

for section in parser.sections:
    if section != 'DEFAULT':
        LOG.debug("Section: %s" % section)
        DATA_TYPES[section] = {}
        LOG.debug("Options: %r" % parser.sections[section].keys())
        #Check that mandatory options are present
        if not set(MANDATORY_OPTIONS) <= set(parser.sections[section].keys()):
            LOG.error("Missing required parameter for type %s in data_types.conf" % section)
            raise Exception
        #Add required options
        for name in MANDATORY_OPTIONS:
            DATA_TYPES[section][name] = parser.sections[section].get(name)[0]
            LOG.debug('    %s = %s' % (name, DATA_TYPES[section][name]))
        LOG.debug('Specifics parameters:')
        #Add specific options
        DATA_TYPES[section]['parameters'] = {}
        for name, value in parser.sections[section].items():
            if name not in MANDATORY_OPTIONS:
                choices = ast.literal_eval(value[0])
                if len(choices) == 0:
                    DATA_TYPES[section]['parameters'][name] = str
                elif len(choices) == 1:
                    DATA_TYPES[section]['parameters'][name] = choices[0]
		else:
		    DATA_TYPES[section]['parameters'][name] = choices
		LOG.debug('    %s = %s' % (name, choices))
        LOG.debug("\n")
