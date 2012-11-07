#!/usr/bin/env python
# -*- coding: utf-8 -*-

from driver import Driver
import serial

class Wattsup(Driver):
    
    def __init__(self, probe_id, **kwargs):
        Driver.__init__(self, probe_id)
        
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
        while not self.terminate:
            packet = self.get_packet()
            value = self.extract_watts(packet)
            self.update_value(value)
    
    def get_packet(self):
        packet = ''
        while True:
            char = self.serial.read(1)
            if len(char) == 0:
                raise ValueError('Invalid packet')
            packet += char
            if char == ';':
                return packet
    
    def extract_watts(self, packet):
        value = float(packet.split(',')[3])/10.0
        return value
