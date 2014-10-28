class debian_pkg {
  package {
    ['python-stdeb', 'devscripts', 'python-all-dev']:
    ensure => installed
  }
}
