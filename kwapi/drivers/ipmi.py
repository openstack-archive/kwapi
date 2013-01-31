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
import uuid

from driver import Driver


class Ipmi(Driver):
    """Driver for IPMI cards."""

    def __init__(self, probe_ids, **kwargs):
        """Initializes the IPMI driver.

        Keyword arguments:
        probe_ids -- list containing the probes IDs
                     (a wattmeter monitor sometimes several probes)
        kwargs -- keywords (cache_directory, interface, host, username,
                  password) defining the IPMI parameters

        """
        Driver.__init__(self, probe_ids, kwargs)
        self.cache_file = self.kwargs.get('cache_directory') + '/' +
        str(uuid.uuid4())
        command = 'ipmitool '
        command += '-I ' + self.kwargs.get('interface') + ' '
        command += '-H ' + self.kwargs.get('host') + ' '
        command += '-U ' + self.kwargs.get('username', 'root') + ' '
        command += '-P ' + self.kwargs.get('password') + ' '
        command += 'sdr dump ' + cache_file
        output, error = subprocess.Popen(command,
                                         shell=True,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT
                                         ).communicate()

    def run(self):
        """Starts the driver thread."""
        while not self.stop_request_pending():
            measurements = {}
            measurements['w'] = self.get_watts()
            self.send_measurements(self.probe_ids[0], measurements)
            time.sleep(1)

    def get_watts(self):
        """Returns the power consumption."""
        command = 'ipmitool '
        command += '-S ' + self.cache_file + ' '
        command += '-I ' + self.kwargs.get('interface') + ' '
        command += '-H ' + self.kwargs.get('host') + ' '
        command += '-U ' + self.kwargs.get('username', 'root') + ' '
        command += '-P ' + self.kwargs.get('password') + ' '
        command += 'sensor reading "System Level" | cut -f2 -d"|"'
        output, error = subprocess.Popen(command,
                                         shell=True,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT
                                         ).communicate()
        return int(output)
