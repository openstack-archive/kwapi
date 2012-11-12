import logging
import sys
from configobj import ConfigObj, Section, flatten_errors
from validate import Validator, ValidateError
import drivers

def driver_check(class_name):
    try:
        getattr(sys.modules['drivers'], class_name)
    except AttributeError:
        raise ValidateError("%s doesn't exist." % class_name)
    return class_name

def get_config(config_file, configspec_file):
    config = ConfigObj(config_file, configspec=configspec_file)
    validator = Validator({'driver': driver_check})
    results = config.validate(validator)
    if results != True:
        for(section_list, key, _) in flatten_errors(config, results):
            if key is not None:
                logging.critical('The "%s" key in the section "%s" failed validation.' % (key, ', '.join(section_list)))
            else:
                logging.critical('The following section was missing:%s.' % ', '.join(section_list))
    else:
        return config
