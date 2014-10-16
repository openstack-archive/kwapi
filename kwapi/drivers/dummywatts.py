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

from random import randrange
import time

from driver import Driver


class DummyWatts(Driver):
    """Dummy driver derived from Driver class. Usefull for tests."""

    def __init__(self, probe_ids, probe_data_type, **kwargs):
        """Initializes the dummy driver.

        Keyword arguments:
        probe_ids -- list containing the probes IDs
                     (a wattmeter monitor sometimes several probes)
        kwargs -- keywords (min_value and max_value)
                  defining the random value interval

        """
        Driver.__init__(self, probe_ids, probe_data_type, kwargs)
        self.min_value = int(kwargs.get('min', 75))
        self.max_value = int(kwargs.get('max', 100))

    def run(self):
        """Starts the driver thread."""
        while not self.stop_request_pending():
            measure_time = time.time()
            for probe_id in self.probe_ids:
                if not probe_id:
                    continue
                measurements = self.create_measurements(probe_id,
                               measure_time,
                               int(randrange(self.min_value, self.max_value+1)))
                self.send_measurements(probe_id, measurements)
            time.sleep(1)
