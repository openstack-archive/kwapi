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

import time

from pysnmp.entity.rfc3413.oneliner import cmdgen

from kwapi.utils import log
from driver import Driver

LOG = log.getLogger(__name__)

class Snmp(Driver):
    """Driver for SNMP based PDUs."""

    def __init__(self, probe_ids, probe_data_type, **kwargs):
        """Initializes the SNMP driver.

        Keyword arguments:
        probe_ids -- list containing the probes IDs
                     (a metricmeter monitor sometimes several probes)
        kwargs -- keyword (protocol, user or community, ip, oid) defining the
                  SNMP parameters
                  Eaton OID is 1.3.6.1.4.1.534.6.6.7.6.5.1.3
                  Raritan OID is 1.3.6.1.4.1.13742.4.1.2.2.1.7

        """
        Driver.__init__(self, probe_ids, probe_data_type, kwargs)
        self.cmd_gen = cmdgen.CommandGenerator()

    def run(self):
        """Starts the driver thread."""
        while not self.stop_request_pending():
            measure_time = time.time()
            metrics_list = self.get_metrics()
            #Sum duplicate probes metrics in a specific dictionnary
            agg_values = {}

            if metrics_list is not None:
                i = 0
                for metrics in metrics_list:
		    probe = self.probe_ids[i]
		    i+=1
                    if not probe:
		        continue
                    # probe_data_type =  {'name':'switch.port.receive.bytes',
                    #                     'type':'Cummulative',
                    #                     'unit':'B'}
                    if self.probe_data_type['type'] == 'Gauge':
		        if not probe in agg_values:
		            agg_values[probe] = 0
		        agg_values[probe] += metrics
		    else:
		        measurements = self.create_measurements(probe,
						                measure_time,
						                metrics)
                        self.send_measurements(probe, measurements)
		#Send each sum of probe
                for probe, agg_value in agg_values.items():
                     measurements = self.create_measurements(probe,
							     measure_time,
							     agg_value)
		     self.send_measurements(probe, measurements)
            time.sleep(self.kwargs.get('resolution', 1))

    def get_metrics(self):
        """Returns the OID field."""
        protocol = self.kwargs.get('protocol')
        if protocol == '1':
            community_or_user = cmdgen.CommunityData(
                self.kwargs.get('community'),
                mpModel=0)
        elif protocol == '2c':
            community_or_user = cmdgen.CommunityData(
                self.kwargs.get('community'),
                mpModel=1)
        elif protocol == '3':
            community_or_user = cmdgen.UsmUserData(self.kwargs.get('user'))
        errorIndication, errorStatus, errorIndex, varBindTable = \
            self.cmd_gen.bulkCmd(
                community_or_user,
                cmdgen.UdpTransportTarget((self.kwargs.get('ip'), 161)),
                1, 0,
                self.kwargs.get('oid'),
                maxRows=len(self.probe_ids),
            )

        if errorIndication:
            LOG.error(errorIndication)
            LOG.error("Request: %s\t%s\t%s\t%s" 
                      % (self.kwargs.get('user'), self.kwargs.get('ip'),
                         self.kwargs.get('oid'), self.probe_ids[0]))
            return None
        else:
            if errorStatus:
                LOG.error('%s at %s' % (
                    errorStatus.prettyPrint(),
                    errorIndex and varBindTable[-1][int(errorIndex) - 1] or '?'
                ))
                return None
            else:
                outlet_list = []
                for varBindTableRow in varBindTable:
                    for name, value in varBindTableRow:
                        outlet_list.append(int(value))
                return outlet_list

