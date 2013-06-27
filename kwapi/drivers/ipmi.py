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

import errno
import os
import subprocess
import time
import uuid

from kwapi.openstack.common import log
from driver import Driver

LOG = log.getLogger(__name__)


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

    def run(self):
        """Starts the driver thread."""
        measurements = {}
        while not self.stop_request_pending():
            watts = self.get_watts()
            if watts is not None:
                measurements['w'] = watts
                self.send_measurements(self.probe_ids[0], measurements)
            time.sleep(1)

    def get_cache_filename(self):
        """Returns the cache filename."""
        return self.kwargs.get('cache_dir') + '/' + \
            str(uuid.uuid5(uuid.NAMESPACE_DNS, self.probe_ids[0]))

    def create_cache(self):
        """Creates the cache file."""
        cache_file = self.get_cache_filename()
        try:
            os.makedirs(self.kwargs.get('cache_dir'))
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise
        command = 'ipmitool '
        command += '-I ' + self.kwargs.get('interface') + ' '
        command += '-H ' + self.kwargs.get('host') + ' '
        command += '-U ' + self.kwargs.get('username', 'root') + ' '
        command += '-P ' + self.kwargs.get('password') + ' '
        command += 'sdr dump ' + cache_file
        child = subprocess.Popen(command,
                                 shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE
                                 )
        output, error = child.communicate()
        if child.returncode == 0:
            return cache_file
        else:
            LOG.error('Failed to download cache from probe %s: %s'
                      % (self.probe_ids[0], error))
            return None

    def get_watts(self):
        """Returns the power consumption."""
        cache_file = self.get_cache_filename()
        # Try to create cache (not a problem if this fails)
        if not os.path.exists(cache_file):
            self.create_cache()
        # Get power consumption
        command = 'ipmitool '
        command += '-S ' + cache_file + ' '
        command += '-I ' + self.kwargs.get('interface') + ' '
        command += '-H ' + self.kwargs.get('host') + ' '
        command += '-U ' + self.kwargs.get('username', 'root') + ' '
        command += '-P ' + self.kwargs.get('password') + ' '
        command += 'sensor reading "' + self.kwargs.get('sensor_name') + '"'
        child = subprocess.Popen(command,
                                 shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE
                                 )
        output, error = child.communicate()
        if child.returncode == 0:
            try:
                return int(output.split('|')[1])
            except ValueError:
                LOG.error('Received data from probe %s are invalid: %s'
                          % (self.probe_ids[0], output))
        else:
            LOG.error('Failed to retrieve data from probe %s: %s'
                      % (self.probe_ids[0], error))
            return None
