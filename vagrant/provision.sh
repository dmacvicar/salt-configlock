#!/bin/bash

zypper -n ar -f http://download.opensuse.org/repositories/systemsmanagement:/saltstack/openSUSE_13.2/systemsmanagement:saltstack.repo
zypper -n in --no-recommends salt-master salt-minion

cat <<EOF > /etc/salt/minion.d/dev.conf
master: localhost

beacons:
  configlock:
    managed:
      lock: True

module_dirs:
  - /vagrant/vagrant/sls
EOF

rcsalt-master restart
rcsalt-minion restart

sleep 10
salt-key -A -y

