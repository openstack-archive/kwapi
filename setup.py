#!/usr/bin/env python
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


import setuptools

setuptools.setup(

    name='kwapi-g5k',
    version='0.3-3',

    description='Grid5000 Monitoring Framework',

    author='François Rossigneux, Laurent Pouilloux, Clement Parisot',
    author_email='laurent.pouilloux@inria.fr',

    url='http://kwapi-g5k.readthedocs.org/en/latest/',

    classifiers=[
        'Development Status :: 4 - Beta',
	'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Topic :: System :: Monitoring',
    ],

    packages=setuptools.find_packages(),
    package_data={'kwapi.plugins.live': ['templates/*', 'static/*.css', 'static/*.png', 'static/*.jpg', 'static/*.gif', 'static/*.js', 'static/select2/*'],
                  'kwapi.plugins.rrd':  ['templates/*', 'static/*.css', 'static/*.png', 'static/*.jpg', 'static/*.js', 'static/select2/*']},

    scripts=['bin/kwapi-g5k-conf', 'bin/kwapi-g5k-check'],

    data_files=[('/etc/kwapi', ['etc/kwapi/api.conf',
                                'etc/kwapi/drivers.conf',
                                'etc/kwapi/rrd.conf',
                                'etc/kwapi/forwarder.conf',
                                'etc/kwapi/daemon.conf',
                                'etc/kwapi/hdf5.conf',
                                'etc/kwapi/live.conf',
                                'etc/kwapi/ganglia.conf']),
                ('/etc/init.d', ['etc/init/kwapi'])],

    install_requires=['flask',
                      'pyserial',
                      'pyzmq',
                      'rrdtool',
                      'execo',
                      'numpy',
                      'pandas',
                      'tables',
                      'numexpr',
                      'httplib2',
                      'pysnmp',
                      'ganglia'],
    entry_points={
        'console_scripts': [
            'kwapi-api = kwapi.plugins.api.app:start',
            'kwapi-drivers = kwapi.drivers.driver_manager:start',
            'kwapi-forwarder = kwapi.forwarder:start',
            'kwapi-rrd = kwapi.plugins.rrd.app:start',
            'kwapi-hdf5 = kwapi.plugins.hdf5.app:start',
            'kwapi-live = kwapi.plugins.live.app:start',
            'kwapi-ganglia = kwapi.plugins.ganglia.app:start']
    }
    
)
