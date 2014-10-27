import 'git.pp'
import 'debian_pkg.pp'
import 'execo.pp'

require 'git'
require 'debian_pkg'
require 'execo'

class kwapi {
  exec { "apt-update":
    command => "/usr/bin/apt-get update"
  }

  git::clone {"clone kwapi-g5k":
    path => "/tmp",
    dir => "kwapi-g5k",
    url => "https://github.com/lpouillo/kwapi-g5k.git",
    require => Exec['apt-update'];
  }->
  git::checkout {"checkout network-monitoring":
    name => "network-monitoring-dev",
    path => "/tmp/kwapi-g5k",
    notify => Exec['generate deb package'];
  }

  exec {
    "generate deb package":
      cwd => '/tmp/kwapi-g5k',
      path => "/usr/bin:/usr/sbin:/bin",
      command => "python setup.py --command-packages=stdeb.command bdist_deb",
      user => root;
  }
  package {
    "python-kwapi-g5k":
      provider => dpkg,
      ensure => latest,
      source => "/tmp/kwapi-g5k/deb_dist/python-kwapi-g5k_0.1-1_all.deb",
      require => Exec['generate deb package'];
  }
  exec {
    "update pandas":
      cwd => '/tmp/kwapi-g5k',
      path => "/usr/bin:/usr/sbin:/bin",
      command => "echo \"deb http://ftp.fr.debian.org/debian wheezy-backports main\" >> /etc/apt/sources.list && apt-get update && apt-get -t wheezy-backports python-pandas",
      user => root,
      require => Package['python-kwapi-g5k']
  }
  
  file {
    '/var/log/kwapi':
      ensure => directory,
      mode   => '0755',
      owner  => root,
      group  => root,
  }
}
