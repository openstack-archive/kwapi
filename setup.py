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
    version='0.1',

    description='Grid5000 Energy Framework',

    author='François Rossigneux, Laurent Pouilloux',
    author_email='francois.rossigneux@inria.fr',

    url='https://github.com/lpouillo/kwapi-g5k',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Grid5000',
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
    package_data={'kwapi.plugins.rrd': ['templates/*', 'static/*'],
                  'kwapi.plugins.live': ['templates/*', 'static/*']},

    scripts=['bin/kwapi-api',
             'bin/kwapi-drivers',
             'bin/kwapi-live',
             'bin/kwapi-rrd',
             'bin/kwapi-forwarder',
             'bin/kwapi-gen-conf',
             'bin/kwapi-hdf5'],

    data_files=[('/etc/kwapi', ['etc/kwapi/api.conf',
                                'etc/kwapi/drivers.conf',
                                'etc/kwapi/live.conf',
                                'etc/kwapi/rrd.conf',
                                'etc/kwapi/forwarder.conf',
                                'etc/kwapi/daemon.conf']),
                ('/etc/init.d', ['etc/init/kwapi'])],

    install_requires=['flask',
                      'pyserial',
                      'pyzmq',
                      'python-rrdtool',
                      'execo',
                      'numpy',
                      'h5py'],
)
