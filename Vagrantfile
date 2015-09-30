ENV['VAGRANT_DEFAULT_PROVIDER'] = 'libvirt'

Vagrant.configure('2') do |config|
  config.vm.box = 'webhippie/opensuse-13.2'
  config.vm.hostname = 'configlock'
  # config.vm.network :private_network, ip: "192.168.0.42"
  config.vm.synced_folder Dir.pwd, '/vagrant', type: '9p'

  config.vm.provision 'shell', path: File.join(Dir.pwd, 'vagrant/provision.sh')
  
end


