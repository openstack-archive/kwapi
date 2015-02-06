# Module:: kwapig5k
# Manifest:: init.pp
#
# Author:: Clement Parisot (<clement.parisot@inria.fr>)
# Date:: Wed, 08 Oct 2014 13:32:38 +0200
# Maintainer:: Clement Parisot (<clement.parisot@inria.fr>)
#

# Class: kwapig5k
#
#
class kwapig5k {
    
    require "apt::backports"
    include 'apt::allowunauthenticated'

    apt::source {
        'python-kwapi-g5k':
        content => "deb http://apt.grid5000.fr/kwapi-g5k /
deb http://apt.grid5000.fr/execo /",
        unauth  => true;
    }

    package {
        'python-kwapi-g5k':
        ensure  => latest,
        notify  => [Service['kwapi'],Exec['Configure kwapi']],
        require => [User['kwapi'],File['source python-kwapi-g5k'],Exec['sources update']];
    }

    group {
        'kwapi':
         ensure => present;
    }

    user {
        'kwapi':
        ensure     => present,
        gid        => 'kwapi',
        home      => '/var/lib/kwapi/',
        managehome => true,
        require    => Group['kwapi'];
    }

    exec {
       "Configure kwapi":
        command     => "kwapi-g5k-conf",
        path        => "/usr/bin:/usr/sbin:/bin",
        user        => "root",
        refreshonly => true,
        subscribe   => Package["python-kwapi-g5k"],
        require     => Package['python-kwapi-g5k'];
    }

    file {
        "/var/log/kwapi":
        ensure  => directory,
        owner   => kwapi,
        group   => kwapi,
        mode    => 0644,
        require => User['kwapi'];
    }
 
    service {
        'kwapi':
        ensure => running,
    }

    cron {
        "kwapi-configure":
        ensure  => present,
        command => "/usr/bin/kwapi-g5k-conf >> /var/log/kwapi/kwapi-g5k-conf.log",
        user    => root,
        hour    => 2,
        minute  => 0;
    }
    file {
    '/etc/logrotate.d/kwapi':
      source  => 'puppet:///modules/kwapig5k/logrotate.conf',
      mode    => '0644',
      owner   => root,
      group   => root,
      require => File['/var/log/kwapi'];
    }
}
