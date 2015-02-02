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

=======================
Working with the Source
=======================

Setting up a Development Sandbox
================================

1. Set up a server or virtual machine.

2. Clone the kwapi project to the machine::

    $ git clone https://github.com/lpouillo/kwapi-g5k.git
    $ cd ./kwapi-g5k

3. Once this is done, use develop option of `setup.py` file to install kwapi locally::

    $ python setup.py develop

4. If some dependant packages are missing, fix them with `pip install`::

    $ pip install -r requirments.txt

4. You can start to hack kwapi. If you are preparing a patch, create a topic branch and switch to
   it before making any changes::

    $ git checkout -b TOPIC-BRANCH

5. Use git to push your changes and ask for a pull request.

6. Package your solution for Debian installation::

    $ python setup.py --command-packages=stdeb.command bdist_deb
    $ cd deb_dist/
    
   All the deb archives are exported in this directory.

7. Import the new generated packages of kwapi-g5k on the remote apt repository.

8. Execute Puppet on the VM to install the latest version of Kwapi or simply run::

    $ apt-get update && apt-get install python-kwapi-g5k

Code Reviews
============

Kwapi uses the GitHub to hos all code and developer documentation contributions. 
You can report an issue or a feature request on this repository.

Bugzilla can also be used for API related bugs or device configuration problems.

.. _Kwapi on GitHub: http://github.com/lpouillo/kwapi-g5k/issues
.. _Bugzilla on Grid'5000: https://intranet.grid5000.fr/bugzilla/
