class git {
  package{
    'git':
      ensure => installed
  }

  define clone ($path, $dir = "", $url, $user = root) {
    exec {
      "git clone $url $dir":
	cwd => $path,
	path => "/usr/bin:/usr/sbin:/bin",
	creates => "$path/$dir",
	user => $user,
	require => Package['git'];
    }
  }

  define checkout ($name = "master", $path, $user = root) {
    exec {
      "git checkout $name":
	cwd => $path,
	path => "/usr/bin:/usr/sbin:/bin",
	user => $user,
	require => Package['git'];
    }
  }
}