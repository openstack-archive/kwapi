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

========
Glossary
========

.. glossary::

   driver
     Software thread running querying a wattmeter and sending the results to
     the plugins.

   forwarder
     Component that forwards plugins subscriptions and metrics.
     Used to minimize the network traffic, or to connect isolated networks
     through a gateway.

   plugin
     An action triggered whenever a meter reaches a certain threshold.

   probe
     A wattmeter sensor. A wattmeter can have only one probe (usually the IPMI
     cards), or multiple probes (usually the PDUs).
