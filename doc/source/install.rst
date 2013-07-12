..
      Copyright 2013 François Rossigneux (Inria)

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

==========
Installing
==========

Installing Kwapi
================

1. Clone the Kwapi git repository to the management server::

   $ git clone https://github.com/stackforge/kwapi.git

2. As a user with ``root`` permissions or ``sudo`` privileges, run the
   Kwapi installer and copy the configuration files::

   $ pip install kwapi
   $ cp -r kwapi/etc/kwapi /etc/

Running Kwapi services
======================

   Start the drivers on all the machines that can access wattmeters::

   $ kwapi-drivers

   Start the forwarder on a remote machine (optional)::

   $ kwapi-forwarder

   Start the API plugin if you want to use Ceilometer::

   $ kwapi-api

   Start the RRD plugin if you want to display graphs in a web browser::

   $ kwapi-rrd
