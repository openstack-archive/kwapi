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

import subprocess
import time

from kwapi.utils import log
from driver import Driver

LOG = log.getLogger(__name__)


class Ipmi(Driver):
    """Driver for IPMI cards."""

    def __init__(self, probe_ids, probe_data_type, **kwargs):
        """Initializes the IPMI driver.

        Keyword arguments:
        probe_ids -- list containing the probes IDs
                     (a wattmeter monitor sometimes several probes)
        kwargs -- keywords (interface, host, username,
                  password) defining the IPMI parameters

        """
        Driver.__init__(self, probe_ids, probe_data_type, kwargs)

    def run(self):
        """Starts the driver thread."""
        if self.set_sensor_name():
            while not self.stop_request_pending():
                watts = self.get_watts()
                if watts is not None:
                    measure_time = time.time()
                    measurements = self.create_measurements(self.probe_ids[0],
                            measure_time, watts)
                    self.send_measurements(self.probe_ids[0], measurements)
                time.sleep(1)

    def set_sensor_name(self):
        """Deduces the sensors name from the IPMI listing, or loads it from
        the config file. Returns True if the sensor name is found.

        """
        names = []
        # Listing
        command = 'ipmitool '
        command += '-I ' + self.kwargs.get('interface') + ' '
        command += '-H ' + self.kwargs.get('host') + ' '
        command += '-U ' + self.kwargs.get('username') + ' '
        command += '-P ' + self.kwargs.get('password') + ' '
        command += 'sensor'
        child = subprocess.Popen(command,
                                 shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE
                                 )
        output, error = child.communicate()
        if child.returncode == 0:
            for line in output.split('\n'):
                if 'Watts' in line:
                    names.append(line.split('|')[0].strip())
            if not names:
                LOG.error('IPMI card does not support wattmeter features')
                return False
            elif not self.kwargs.get('sensor') and len(names) == 1:
                self.kwargs['sensor'] = names[0]
                return True
            elif not self.kwargs.get('sensor') in names:
                LOG.error('Sensor name not found')
                return False
            else:
                return True
        else:
            LOG.error('Failed to list the sensors')
            return None

    def get_watts(self):
        # Get power consumption
        command = 'ipmitool '
        command += '-I ' + self.kwargs.get('interface') + ' '
        command += '-H ' + self.kwargs.get('host') + ' '
        command += '-U ' + self.kwargs.get('username') + ' '
        command += '-P ' + self.kwargs.get('password') + ' '
        command += 'sensor reading "' + self.kwargs.get('sensor') + '"'
        child = subprocess.Popen(command,
                                 shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE
                                 )
        output, error = child.communicate()
        if child.returncode == 0:
            try:
                return float(output.split('|')[1])
            except ValueError:
                LOG.error('Received data from probe %s are invalid: %s'
                          % (self.probe_ids[0], output))
        else:
            LOG.error('Failed to retrieve data from probe %s: %s'
                      % (self.probe_ids[0], error))
            return None
