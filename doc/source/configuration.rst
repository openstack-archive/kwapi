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

=====================
Configuration Options
=====================

Kwapi drivers specific
======================

The following table lists the Kwapi drivers specific options in the drivers
configuration file. For information we are listing the configuration elements
that we use after the Kwapi drivers specific elements.

===============================  ====================================  ==============================================================
Parameter                        Default                               Note
===============================  ====================================  ==============================================================
probes_endpoint                  ipc:///tmp/kwapi-drivers              Endpoint where the drivers send their measurements
                                                                       ipc://<file> or tcp://<host>:<port>
enable_signing                   true                                  Enable message signing between drivers and plugins
metering_secret                  change this or be hacked              Secret value for signing metering messages
check_drivers_interval           60                                    Check drivers at the specified interval and restart them if
                                                                       they are crashed
===============================  ====================================  ==============================================================

The configuration file contains a section for each wattmeter.

A sample configuration file can be found in `drivers.conf`_.

.. _drivers.conf: https://github.com/lpouillo/kwapi-g5k/blob/master/etc/kwapi/drivers.conf

Kwapi plugin API specific
=========================

The following table lists the Kwapi API specific options in the API
configuration file. For information we are listing the configuration
elements that we use after the Kwapi API specific elements.

===============================  ====================================  ==============================================================
Parameter                        Default                               Note
===============================  ====================================  ==============================================================
api_port                         5000                                  API port
probes_endpoint                  ipc:///tmp/kwapi-forwarder            Endpoint where the measurements are received
signature_checking               true                                  Enable the verification of signed metering messages
driver_metering_secret           change this or be hacked              Secret value for verifying signed metering messages
cleaning_interval                300                                   Delete the probes that have not been updated during the
                                                                       specified interval
===============================  ====================================  ==============================================================

A sample configuration file can be found in `api.conf`_.

.. _api.conf: https://github.com/lpouillo/kwapi-g5k/blob/master/etc/kwapi/api.conf

Kwapi plugin RRD specific
=========================

The following table lists the Kwapi RRD specific options in the RRD
configuration file. For information we are listing the configuration
elements that we use after the Kwapi RRD specific elements.

===============================  ====================================  ==============================================================
Parameter                        Default                               Note
===============================  ====================================  ==============================================================
probes_endpoint                  ipc:///tmp/kwapi-forwarder            Endpoint where the measurements are received
signature_checking               true                                  Enable the verification of signed metering messages
driver_metering_secret           change this or be hacked              Secret value for verifying signed metering messages
rrd_dir                          /var/lib/kwapi/kwapi-rrd              The directory where are stored RRD files
===============================  ====================================  ==============================================================

A sample configuration file can be found in `rrd.conf`_.

.. _rrd.conf: https://github.com/lpouillo/kwapi-g5k/blob/master/etc/kwapi/rrd.conf

Kwapi plugin Live specific
==========================

The following table lists the Kwapi Live specific options in the Live
configuration file. For information we are listing the configuration
elements that we use after the Kwapi Live specific elements.

===============================  ====================================  ==============================================================
Parameter                        Default                               Note
===============================  ====================================  ==============================================================
live_port                        8080                                  Port used to display webpages
probes_endpoint                  ipc:///tmp/kwapi-forwarder            Endpoint where the measurements are received
signature_checking               true                                  Enable the verification of signed metering messages
driver_metering_secret           change this or be hacked              Secret value for verifying signed metering messages
png_dir                          /var/lib/kwapi/kwapi-png              The directory where are stored PNG files
rrd_dir                          /var/lib/kwapi/kwapi-rrd              The directory where are stored RRD files
currency                         €                                     The currency symbol used in graphs
kwh_price                        0.125                                 The kWh price used in graphs
hue                              100                                   The hue of the graphs
max_watts                        400                                   The maximum value of the summary graph
refresh_interval                 5                                     The webpage auto-refresh interval
===============================  ====================================  ==============================================================

A sample configuration file can be found in `live.conf`_.

.. _live.conf: https://github.com/lpouillo/kwapi-g5k/blob/master/etc/kwapi/live.conf

.. warning:: Be sure that `rrd_dir` directory is the same in RRD Plugin and Live plugin

Kwapi plugin Ganglia specific
=============================

The following table lists the Kwapi Ganglia specific options in the Ganglia
configuration file. For information we are listing the configuration
elements that we use after the Kwapi API specific elements.

===============================  ====================================  ==============================================================
Parameter                        Default                               Note
===============================  ====================================  ==============================================================
ganglia_server                   udp://239.2.11.71:8649                Ganglia server address
probes_endpoint                  ipc:///tmp/kwapi-forwarder            Endpoint where the measurements are received
signature_checking               true                                  Enable the verification of signed metering messages
driver_metering_secret           change this or be hacked              Secret value for verifying signed metering messages
===============================  ====================================  ==============================================================

A sample configuration file can be found in `ganglia.conf`_.

.. _ganglia.conf: https://github.com/lpouillo/kwapi-g5k/blob/master/etc/kwapi/ganglia.conf

General options
===============

The following is the list of options that we use:

===========================  ====================================  ==============================================================
Parameter                    Default                               Note
===========================  ====================================  ==============================================================
log_file                                                           Log output to a named file
verbose                      true                                  Print more verbose output
===========================  ====================================  ==============================================================

Kwapi forwarder specific
=========================

The following table lists the Kwapi forwarder specific options in the forwarder
configuration file. For information we are listing the configuration elements that
we use after the Kwapi forwarder specific elements.

===============================  ====================================  ==============================================================
Parameter                        Default                               Note
===============================  ====================================  ==============================================================
forwarder_endpoint               ipc:///tmp/kwapi-forwarder            Endpoint where the measurements are forwarded and where the
                                                                       plugins subscriptions are received
probes_endpoint                  ipc:///tmp/kwapi-drivers              Endpoint where the drivers send their measurements.
                                                                       ipc://<file> or tcp://<host>:<port>
===============================  ====================================  ==============================================================

A sample configuration file can be found in `forwarder.conf`_.

.. _forwarder.conf: https://github.com/lpouillo/kwapi-g5k/blob/master/etc/kwapi/forwarder.conf


Kwapi Daemon specific
=====================

The following table lists the Kwapi service specific options in the daemon
configuration file.

Set a parameter to **false** will not start the corresponding plugin/driver when you start the service.

.. warning:: Always run `service kwapi stop` **BEFORE** modifying any of the following parameters !

===============================  ====================================  ==============================================================
Parameter                        Default                               Note
===============================  ====================================  ==============================================================
KWAPI_DRIVERS                    true                                  Start Kwapi drivers in kwapi service
KWAPI_FORWARDER                  true                                  Start Kwapi forwarder in kwapi service
KWAPI_API                        true                                  Start Kwapi api in kwapi service
KWAPI_RRD                        true                                  Start Kwapi rrd in kwapi service
KWAPI_HDF5                       true                                  Start Kwapi hdf5 in kwapi service
KWAPI_LIVE                       true                                  Start Kwapi live in kwapi service
KWAPI_GANGLIA                    true                                  Start Kwapi ganglia in kwapi service
===============================  ====================================  ==============================================================

A sample configuration file can be found in `daemon.conf`_.

.. _daemon.conf: https://github.com/lpouillo/kwapi-g5k/blob/master/etc/kwapi/daemon.conf


