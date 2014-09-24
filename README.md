khaleesi-settings
=================

settings required for executing khaleesi provisioned openstack environments.

Use with khaleesi code repository
https://github.com/redhat-openstack/khaleesi


Example Workflow
=================
git clone https://github.com/redhat-openstack/khaleesi.git
git clone https://github.com/redhat-openstack/khaleesi-settings.git

virtualenv venv
source venv/bin/activate
pip install ansible
cd khaleesi
cd tools/ksgen
python setup.py develop
cd ../..

On Fedora, yum install ansible

cat > ansible.cfg << EOF
[defaults]
host_key_checking = False
roles_path = ./roles
library = ./library:/usr/share/ansible/
lookup_plugins = ./plugins/lookups
EOF


ksgen --config-dir=$CONFIG_BASE/settings generate \
    --rules-file=$CONFIG_BASE/rules/packstack-rdo-aio.yml \
    --provisioner openstack \
    --provisioner-site CHANGE_ME \
    --provisioner-site-user CHANGE_ME \
    --product-version=juno \
    --product-version-repo=production \
    --distro=centos-7.0 \
    --product-version-workaround=centos-7.0 \
    --workarounds=enabled \
    --installer-network=neutron \
    --installer-network-variant=gre \
    --tester-tests=minimal \
    --extra-vars provisioner.password=CHANGE_ME \
    ksgen_settings.yml

./run.sh --verbose --use ksgen_settings.yml  playbooks/packstack.yml
