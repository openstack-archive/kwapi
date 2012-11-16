# -*- coding: utf-8 -*-

import logging
import serial
from serial.serialutil import SerialException

from driver import Driver

class Wattsup(Driver):
    """Driver for Wattsup wattmeters."""
    
    def __init__(self, probe_ids, **kwargs):
        """Initializes the Wattsup driver.
        
        Keyword arguments:
        probe_ids -- list containing the probes IDs (a wattmeter monitor sometimes several probes
        kwargs -- keyword (device) defining the device to read (/dev/ttyUSB0)
        
        """
        Driver.__init__(self, probe_ids, kwargs)
        
        # Configure serial port
        self.serial = serial.Serial(
            port=kwargs.get('device', '/dev/ttyUSB0'),
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
    
    def run(self):
        """Starts the driver thread."""
        while not self.stop_request_pending():
            try:
                packet = self.get_packet()
            except SerialException:
                self.serial.close()
                self.stop()
            value = self.extract_watts(packet)
            self.update_value(self.probe_ids[0], value)
    
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
