class execo {
  package{
    'wget':
      ensure => installed;
  }

  exec {
    "get execo":
      cwd => '/tmp',
      path => "/usr/bin:/usr/sbin:/bin",
      user => root,
      command => "wget http://execo.gforge.inria.fr/downloads/execo-2.3.tar.gz && tar xzf execo-2.3.tar.gz && cd execo-2.3/ && python setup.py install --user",
      require => Package['wget'];
  }
}
