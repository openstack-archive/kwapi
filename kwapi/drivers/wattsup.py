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

import serial
from serial.serialutil import SerialException
import time

from driver import Driver


class Wattsup(Driver):
    """Driver for Wattsup wattmeters."""

    def __init__(self, probe_ids, data_type, **kwargs):
        """Initializes the Wattsup driver.

        Keyword arguments:
        probe_ids -- list containing the probes IDs
                     (a wattmeter monitor sometimes several probes)
        kwargs -- keyword (device) defining the device to read (/dev/ttyUSB0)

        """
        Driver.__init__(self, probe_ids, data_type, kwargs)

    def run(self):
        """Starts the driver thread."""
        # Configure serial port
        self.serial = serial.Serial(
            port=self.kwargs.get('device', '/dev/ttyUSB0'),
            baudrate=115200,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=2,
        )
        # Clear memory
        self.serial.write('#R,W,0;')
        self.serial.read(256)
        # Start external logging with interval = 1
        self.serial.write('#L,W,3,E,1,1;')
        self.serial.read(256)
        # Take measurements
        while not self.stop_request_pending():
            try:
                packet = self.get_packet()
            except SerialException:
                self.serial.close()
                self.stop()
            measure_time = time.time()
            measurements = self.create_measurements(self.probe_ids[0],
                                                    measure_time,
                                                    self.extract_watts(packet))
            self.send_measurements(self.probe_ids[0], measurements)

    def get_packet(self):
        """Returns the next packet sent by the wattmeter."""
        packet = ''
        while True:
            char = self.serial.read(1)
            if len(char) == 0:
                raise ValueError('Invalid packet')
            packet += char
            if char == ';':
                return packet

    def extract_watts(self, packet):
        """Extracts the consumption data (watts) from the packet."""
        value = float(packet.split(',')[3])/10.0
        return value
