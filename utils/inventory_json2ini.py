import ConfigParser
import json
import argparse
import sys
import collections
import yaml
import os

import pprint

class CompatConfigParser(ConfigParser.ConfigParser):

    def __init__(self, defaults=None, dict_type=None, allow_no_value=False):
        if sys.version_info[1] == 7:
            ConfigParser.ConfigParser.__init__(self, defaults, dict_type, allow_no_value)
        elif sys.version_info[1] == 6:
            ConfigParser.ConfigParser.__init__(self, defaults, dict_type)

    def set_novalue(self, section, key):
        if sys.version_info[1] == 7:
            self.set(section, key)
        elif sys.version_info[1] == 6:
            self.set(section, key, "No Value")

resources_filename_default = "results.json"
inventory_filename_default = "inventory.ini"

parser = argparse.ArgumentParser(description="Convert provisioner resources"
                                 "json format to inventory ini format for "
                                 "ansible")
resources_files_group = parser.add_mutually_exclusive_group()
parser.add_argument('-i', '--inventory-file',
                    dest='inventory_filename',
                    default=inventory_filename_default,
                    help="the output inventory file (default: %s)"
                          % (inventory_filename_default))
resources_files_group.add_argument('-l', '--resources-list',
                                    dest='resources_list',
                                    help="comma separated list of input resources file",
                                    nargs='*')
resources_files_group.add_argument('-r', '--resources_file',
                                    dest='resources_filename',
                                    help="the input resources file (default: %s)"
                                        % (resources_filename_default))


args, unknown = parser.parse_known_args(sys.argv)

if args.resources_filename:
    args.resources_list = []
    args.resources_list.append(args.resources_filename)


inventory = CompatConfigParser(None, collections.OrderedDict, True)

inventory.add_section('local')
inventory.set_novalue('local', 'localhost')
inventory.add_section('local:vars')
inventory.set('local:vars', 'ansible_connection', 'local')

try:
    os.stat("host_vars")
except OSError:
    os.mkdir("host_vars")

# reopen nodes.yml tocorrect nodes.yml node names
# with results from central provisioner
with open("nodes.yml", "r") as nodes_file:
    nodes = yaml.load(nodes_file)

for resources_filename in args.resources_list:

    with open(resources_filename, "r") as resources_file:
        resources_provisioned = json.load(resources_file)

    hosts = resources_provisioned['resources']

    for host in hosts:
        grouplist = host['metadata']['groups'].split(',')
        for node in host['nodes']:
            for group in grouplist:
                try:
                    inventory.add_section(group)
                except:
                    pass
                inventory.set_novalue(group, node['name'])

            host_vars = {
                "ansible_ssh_host": node['ip'],
            }
            for var in host['metadata'].keys():
                if var == "remote_user":
                    # CI OPS CENTRAL uses always root
                    host_vars['ansible_ssh_user'] = 'root'
                elif var == 'key_name':
                    host_vars['ansible_ssh_private_key_file'] = host['metadata']['key_name'] + '.pem'
                elif var == 'name':
                    # correct nodes.yml node names with results from central provisioner
                    khaleesi_name = host['metadata']['name']
                    ci_ops_name = host['nodes'][0]['name']
                    for key, value in nodes.iteritems():
                        if value == khaleesi_name:
                            nodes[key] = ci_ops_name
                    for element in nodes['nodes']:
                        # CI OPS CENTRAL uses always root
                        element['remote_user'] = 'root'
                        for key, value in element.iteritems():
                            if value == khaleesi_name:
                                element[key] = ci_ops_name
                else:
                    host_vars[var] = host['metadata'][var]

            with open("host_vars/" + node['name'], "w") as host_vars_filename:
                host_vars_filename.write(yaml.safe_dump(host_vars, default_flow_style=False, canonical=False))

with open("nodes.yml", "w") as nodes_file:
    nodes_file.write(yaml.safe_dump(nodes))

with open(args.inventory_filename, "w") as inventory_file:
    inventory.write(inventory_file)


