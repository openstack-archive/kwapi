#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils.core import setup

setup(

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
   
    packages=['kwapi', 'kwapi.api', 'kwapi.drivers'],
   
    scripts=['bin/kwapi-api',
             'bin/kwapi-drivers'],
   
    data_files=[('/etc/kwapi', ['etc/kwapi/kwapi.conf'])],
    
    install_requires=['configobj', 'flask', 'pyserial', 'python-keystoneclient', 'pyzmq', 'requests']
    
    )
