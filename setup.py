#!/usr/bin/env python
# -*- coding: utf-8 -*-

import setuptools

setuptools.setup(
    
    name='kwapi',
    version='1.0',
    
    description='Energy Efficiency Architecture',
    
    author='François Rossigneux',
    author_email='francois.rossigneux@inria.fr',
    
    url='http://gitorious.ow2.org/xlcloud/kwapi',
    
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Framework :: Setuptools Plugin',
        'Environment :: OpenStack',
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
    package_data={'kwapi.plugins.rrd': ['templates/*.html']},
    
    scripts=['bin/kwapi-api',
             'bin/kwapi-drivers',
             'bin/kwapi-rrd'],
    
    data_files=[('/etc/kwapi', ['etc/kwapi/api.conf', 'etc/kwapi/drivers.conf', 'etc/kwapi/rrd.conf'])],
    
    install_requires=['flask', 'pyserial', 'python-keystoneclient', 'pyzmq', 'py-rrdtool']
    
    )
