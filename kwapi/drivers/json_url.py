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

import json
import urllib2
import time

from kwapi.utils import log
from driver import Driver

LOG = log.getLogger(__name__)


class Json_url(Driver):
    """Driver for Json URL interface."""

    def __init__(self, probe_ids, probe_data_type, **kwargs):
        """Initializes the Json URL driver.
        Keyword arguments:
        probe_ids -- list containing the probes IDs
                     (a wattmeter monitor sometimes several probes)
        kwargs -- keyword (url) defining the Json URL driver parameters

        """
        Driver.__init__(self, probe_ids, probe_data_type, kwargs)

    def run(self):
        """Starts the driver thread."""
        while not self.stop_request_pending():
            json_content = json.load(urllib2.urlopen(self.kwargs.get('url')))
            for probe_id in self.probe_ids:
                probe = json_content.get(probe_id.split('.')[1])
                # Grid5000 specific as we declare probes as site.cluster-#
                if probe:
                    measurements = self.create_measurements(probe_id,
                                                            probe['timestamp'],
                                                            probe['watt'])
                    self.send_measurements(probe_id, measurements)
            time.sleep(1)


