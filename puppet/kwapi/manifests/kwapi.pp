import 'hdf5.pp'
import 'python.pp'
import 'rrd.pp'
import 'git.pp'
import 'other_packages.pp'

require 'git'
require 'hdf5'
require 'rrd'
require 'other_packages'
require 'python'

class kwapi {
  exec { "apt-update":
    command => "/usr/bin/apt-get update"
  }->
  git::clone {"clone kwapi-g5k":
    path => "/tmp",
    dir => "kwapi-g5k",
    url => "https://github.com/lpouillo/kwapi-g5k.git";
  }->
  git::checkout {"checkout network-monitoring":
    name => "network-monitoring",
    path => "/tmp/kwapi-g5k";
  }->
  exec { "easy_install execo":
    command => "/usr/bin/easy_install execo"
  }->
  python::pip_install{"install requirements":
    path_requirements_file => '/tmp/kwapi-g5k/requirements.txt',
    path => '/tmp/kwapi-g5k';
  }->
  exec {
    "setup":
      cwd => '/tmp/kwapi-g5k',
      path => "/usr/bin:/usr/sbin:/bin",
      command => "python setup.py install",
      user => root;
  }
  file {
    '/var/log/kwapi':
      ensure => directory,
      mode   => '0755',
      owner  => root,
      group  => root,
  }
}
