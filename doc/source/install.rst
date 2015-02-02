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

Installing Kwapi from source
============================

1. Clone the Kwapi git repository to the management server::

   $ git clone https://github.com/lpouillo/kwapi-g5k.git

2. As a user with ``root`` permissions or ``sudo`` privileges, run the
   Kwapi installer and copy the configuration files::

   $ pip install kwapi-g5k
   $ cp -r kwapi-g5k/etc/kwapi /etc/


Installing Kwapi on Grid'5000
=============================

1. Create a VM on the site you want to monitor. You can create a domU with Xen or KVM. The command should be similar to this one::
   
   $ http_proxy="http://proxy:3128/" xen-create-image --hostname=kwapi --ip=ip_address --dist wheezy --role=udev
   
   You can find more informations about this procedure here: `<https://www.grid5000.fr/mediawiki/index.php/Services_Xen_DomU>`_

2. Start your VM::
   
   $ xm create /etc/xen/kwapi.cfg

3. Install configuration tool on the VM. Puppet manifests and files are available in **puppet-repo**. You must install the right version of Puppet used in Grid'5000. Installation procedure can be find here: `Puppet <https://www.grid5000.fr/mediawiki/index.php/Puppet>`_. After the certificate signing procedure, you should have a new Puppet node named **kwapi.site.grid5000.fr**.

4. Configure Kwapi with Puppet. You have to add additional classes on your new Puppet node. Use ``puppetplay`` to add **kwapi-g5k** class on the node::

   $ puppetplay node kwapi.site.grid5000.fr --edit --add-classes kwapi-g5k

5. Wait one hour or use `Capistrano tool <https://www.grid5000.fr/mediawiki/index.php/Puppet_deployment_with_Capistrano>`_ to force Puppet execution on the VM.::

   $ cap puppet:production HOST=kwapi.site.grid5000.fr MODULE=all SITE=site

6. Your VM is now configured with latest Grid'5000 version of Kwapi. You can connect on the node to check Kwapi service status.::

   $ ssh kwapi.site.g5kadmin
   $ sudo service kwapi status


Running Kwapi modules as daemon
===============================

Kwapi can be started, stoped, restarted with the service command::

   $ sudo service kwapi start|stop|restart

This command will start kwapi as a daemon and run the modules indicated in ``/etc/kwapi/daemon.conf`` file.

Running Kwapi modules in foreground (debugging)
===============================================
   
If you want to manage each Kwapi module individually (drivers and plugins), you can run the following commands.

* Start the drivers on all the configured machines::

   $ kwapi-drivers

* Start the forwarder on this machine and a remote machine (optional)::

   $ kwapi-forwarder

* Start the API plugin if you want to access metrics with the API::

   $ kwapi-api

* Start the RRD plugin if you want to store data as RRD (mandatory to display graphs in a web browser)::

   $ kwapi-rrd

* Start the HDF5 plugin if you want to store fine grained datas::

  $ kwapi-hdf5

* Start Live plugin to active Web visualisation of your mesures::

  $ kwapi-live

* Start Ganglia plugin to push data to the remote Ganglia server::

  $ kwapi-ganglia

.. warning:: Don't forget to **stop** Kwapi daemon service before activating modules in foreground or it will result on conflict problems and data corruption !
