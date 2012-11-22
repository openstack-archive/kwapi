# -*- coding: utf-8 -*-

"""Kwapi configuration."""

from optparse import OptionParser
import os
import sys

from configobj import ConfigObj, Section, flatten_errors
from validate import Validator, ValidateError

import drivers

def driver_exists(class_name):
    """Checks if class_name is a real Python class."""
    try:
        getattr(sys.modules['kwapi.drivers'], class_name)
    except AttributeError:
        raise ValidateError("%s doesn't exist." % class_name)
    return class_name

def get_drivers():
    """Returns a generator over all drivers (class_name, probe_ids, kwargs)."""
    for key in CONF.keys():
        if isinstance(CONF[key], Section):
            class_name = CONF[key]['driver']
            probe_ids = CONF[key]['probes']
            try:
                kwargs = CONF[key]['parameters']
            except KeyError:
         	    kwargs = {}
            yield class_name, probe_ids, kwargs

def get_config(config_file):
    """Validates config_file and returns a ConfigObj (dictionary-like) if success."""
    spec = cfg.split("\n")
    try:
        config = ConfigObj(infile=config_file, configspec=spec, file_error=True)
    except IOError:
        print 'Error: %s not found' % config_file
    else:
        validator = Validator({'driver': driver_exists})
        results = config.validate(validator)
        if results != True:
            for(section_list, key, _) in flatten_errors(config, results):
                if key is not None:
                    print 'Error: the "%s" key in the section "%s" failed validation' % (key, ', '.join(section_list))
                else:
                    print 'Error: the following section was missing:%s' % ', '.join(section_list)
        else:
            return config

# Config file format specifications
cfg = """
acl_enabled = boolean
acl_auth_url = string
api_log = string
api_port = integer
collector_socket = string
check_drivers_interval = integer
collector_cleaning_interval = integer
drivers_log = string

[__many__]
    probes = string_list
    driver = driver
"""

parser = OptionParser()
parser.add_option('-f', metavar="FILE", default='/etc/kwapi/kwapi.conf', help='configuration file')
(options, args) = parser.parse_args()

CONF = get_config(options.f)
