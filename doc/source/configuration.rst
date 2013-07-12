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
configuration file. Please note that Kwapi uses openstack-common extensively,
which requires that the other parameters are set appropriately. For information
we are listing the configuration elements that we use after the Kwapi drivers
specific elements.

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

.. _drivers.conf: https://github.com/stackforge/kwapi/blob/master/etc/kwapi/drivers.conf

Kwapi plugin API specific
=========================

The following table lists the Kwapi API specific options in the API
configuration file. Please note that Kwapi uses openstack-common extensively,
which requires that the other parameters are set appropriately. For information
we are listing the configuration elements that we use after the Kwapi API
specific elements.

===============================  ====================================  ==============================================================
Parameter                        Default                               Note
===============================  ====================================  ==============================================================
api_port                         5000                                  API port
probes_endpoint                  ipc:///tmp/kwapi-forwarder            Endpoint where the measurements are received
signature_checking               true                                  Enable the verification of signed metering messages
driver_metering_secret           change this or be hacked              Secret value for verifying signed metering messages
acl_enabled                      true                                  Check the Keystone tokens provided by the clients
policy_file                      /etc/kwapi/policy.json                Policy file
cleaning_interval                300                                   Delete the probes that have not been updated during the
                                                                       specified interval
===============================  ====================================  ==============================================================

A sample configuration file can be found in `api.conf`_.

.. _api.conf: https://github.com/stackforge/kwapi/blob/master/etc/kwapi/api.conf

Keystone Middleware Authentication
----------------------------------

The following table lists the Keystone middleware authentication options which are used to get admin token.
Please note that these options need to be under [keystone_authtoken] section.

===============================  ====================================  ==============================================================
Parameter                        Default                               Note
===============================  ====================================  ==============================================================
auth_host                                                              The host providing the Keystone service API endpoint for
                                                                       validating and requesting tokens
auth_port                        35357                                 The port used to validate tokens
auth_protocol                    https                                 The protocol used to validate tokens
auth_uri                         auth_protocol://auth_host:auth_port   The full URI used to validate tokens
admin_token                                                            Either this or the following three options are required. If
                                                                       set, this is a single shared secret with the Keystone
                                                                       configuration used to validate tokens.
admin_user                                                             User name for retrieving admin token
admin_password                                                         Password for retrieving admin token
admin_tenant_name                                                      Tenant name for retrieving admin token
signing_dir                                                            The cache directory for signing certificate
certfile                                                               Required if Keystone server requires client cert
keyfile                                                                Required if Keystone server requires client cert. This can be
                                                                       the same as certfile if the certfile includes the private key.
===============================  ====================================  ==============================================================

Kwapi plugin RRD specific
=========================

The following table lists the Kwapi RRD specific options in the RRD
configuration file. Please note that Kwapi uses openstack-common extensively,
which requires that the other parameters are set appropriately. For information
we are listing the configuration elements that we use after the Kwapi RRD
specific elements.

===============================  ====================================  ==============================================================
Parameter                        Default                               Note
===============================  ====================================  ==============================================================
rrd_port                         8080                                  Port used to display webpages
probes_endpoint                  ipc:///tmp/kwapi-forwarder            Endpoint where the measurements are received
signature_checking               true                                  Enable the verification of signed metering messages
driver_metering_secret           change this or be hacked              Secret value for verifying signed metering messages
png_dir                          /var/lib/kwapi/kwapi-png              The directory where are stored PNG files
rrd_dir                          /var/lib/kwapi/kwapi-rrd              The directory where are stored RRD files
currency                         €                                     The currency symbol used in graphs
kwh_price                        0.125                                 The kWh price used in graphs
hue                              100                                   The hue of the graphs
max_watts                        200                                   The maximum value of the summary graph
refresh_interval                 5                                     The webpage auto-refresh interval
===============================  ====================================  ==============================================================

A sample configuration file can be found in `rrd.conf`_.

.. _rrd.conf: https://github.com/stackforge/kwapi/blob/master/etc/kwapi/rrd.conf

General options
===============

The following is the list of openstack-common options that we use:

===========================  ====================================  ==============================================================
Parameter                    Default                               Note
===========================  ====================================  ==============================================================
log_file                                                           Log output to a named file
verbose                      true                                  Print more verbose output
===========================  ====================================  ==============================================================

Kwapi forwarder specific
=========================

The following table lists the Kwapi forwarder specific options in the forwarder
configuration file. Please note that Kwapi uses openstack-common extensively,
which requires that the other parameters are set appropriately. For information
we are listing the configuration elements that we use after the Kwapi forwarder
specific elements.

===============================  ====================================  ==============================================================
Parameter                        Default                               Note
===============================  ====================================  ==============================================================
forwarder_endpoint               ipc:///tmp/kwapi-forwarder            Endpoint where the measurements are forwarded and where the
                                                                       plugins subscriptions are received
probes_endpoint                  ipc:///tmp/kwapi-drivers              Endpoint where the drivers send their measurements.
                                                                       ipc://<file> or tcp://<host>:<port>
===============================  ====================================  ==============================================================

The configuration file contains a section for each wattmeter.

A sample configuration file can be found in `forwarder.conf`_.

.. _forwarder.conf: https://github.com/stackforge/kwapi/blob/master/etc/kwapi/forwarder.conf
