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

===========================================
Welcome to Kwapi's developer documentation!
===========================================

Kwapi is a framework designed for acquiring energy consumption metrics. It
allows to upload metrics from various wattmeters to Ceilometer.

Its architecture is based on a layer of drivers, which retrieve measurements
from wattmeters, and a layer of plugins that collect and process them. The
communication between these two layers goes through a bus. In the case of a
distributed architecture, a plugin can listen to several drivers at remote
locations.

Drivers and plugins are easily extensible to support other types of wattmeters,
and provide other services.

What is the purpose of the project and vision for it?
=====================================================

Kwapi could be used to do:
  * Energy monitoring of data centers
  * Usage-based billing
  * Efficient scheduling

It aims at supporting various wattmeters, being scalable and easily extensible.

This documentation offers information on how Kwapi works and how to contribute
to the project.

Table of contents
=================

.. toctree::
   :maxdepth: 2

   install
   architecture
   configuration

   contributing/index
   glossary

.. update index

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
