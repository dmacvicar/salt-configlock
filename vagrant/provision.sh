#!/bin/bash

zypper -n ar -f http://download.opensuse.org/repositories/systemsmanagement:/saltstack/openSUSE_13.2/systemsmanagement:saltstack.repo
zypper -n ar -f http://download.opensuse.org/repositories/devel:/languages:/python/openSUSE_13.2/devel:languages:python.repo

zypper -n --gpg-auto-import-keys in --no-recommends salt-master salt-minion
zypper -n --gpg-auto-import-keys in --no-recommends python-certifi gcc python-devel libgit2-devel

cat <<EOF > /etc/salt/minion.d/dev.conf
master: localhost

beacons:
  configlock:
    managed:
      lock: True

module_dirs:
  - /vagrant/vagrant/sls
EOF

cat <<EOF > /etc/salt/master.d/dev.conf
file_roots:
  base:
    - /vagrant/vagrant/sls
EOF

rcsalt-master restart
rcsalt-minion restart

sleep 10
salt-key -A -y

