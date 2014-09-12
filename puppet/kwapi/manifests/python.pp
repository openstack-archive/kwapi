class python {
  package {
    ['python', 'python-dev', 'python-pip']:
    ensure => installed
  }

  define pip_install($path_requirements_file,$path, $user = root){
    exec {
      "pip install -r ${path_requirements_file}":
      cwd => $path,
      path => "/usr/bin:/usr/sbin:/bin",
      user => $user,
      tries => 3,
      require => Package['python-pip'];
    }

  }
}
