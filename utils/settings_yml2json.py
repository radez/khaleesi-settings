import yaml
import json
import argparse
import sys
import os
import pprint
import ast

from novaclient.v1_1 import client as os_novaclient
from jinja2 import Environment, FileSystemLoader, DebugUndefined, DictLoader

settings_filename_default = "settings.yml"
resources_filename_default = "topology.json"

project_defaults_filename = "project_defaults.json"
env_inject_filename = "envinject-wrapper.props"

parser = argparse.ArgumentParser(description="Convert khaleesi settings yaml"
                                 " format to resource json format for "
                                 "standard provisioning")
parser.add_argument('-P', '--settings-path',
                    dest='settings_path',
                    required=True,
                    help="the path with khaleesi settings")
parser.add_argument('-t', '--topology',
                    dest='topology',
                    required=True,
                    help="the topology to be converted")
parser.add_argument('-i', '--installer',
                    dest='installer',
                    required=True,
                    help="the installer to be used in this build")
parser.add_argument('-s', '--settings-file',
                    dest='settings_filename',
                    default=settings_filename_default,
                    help="the input settings file (default: %s)"
                          % (settings_filename_default))
parser.add_argument('-r', '--resources-file',
                    dest='resources_filename',
                    default=resources_filename_default,
                    help="the output resources file (default: %s)"
                          % (resources_filename_default))


args, unknown = parser.parse_known_args(sys.argv)

topologies_path = args.settings_path + os.sep + args.installer + os.sep + "topologies"
template_env = Environment(loader=FileSystemLoader(topologies_path), undefined=DebugUndefined)
nodes_template = template_env.get_template(args.topology + '_nodes.yml')
with open(args.settings_filename, "r") as settings_file:
    settings = yaml.load(settings_file)


# Two passes are needed because node names are defined with variables set on the same document
intermediate_template_data = nodes_template.render(settings)
intermediate_settings = yaml.load(intermediate_template_data)
pprint.pprint(intermediate_settings)
intermediate_template_dict = {"intermediate_template_data": intermediate_template_data}
intermediate_template_env = Environment(loader=DictLoader(intermediate_template_dict))
intermediate_template = intermediate_template_env.get_template("intermediate_template_data")
nodes_yaml = intermediate_template.render(intermediate_settings)
nodes_settings = yaml.load(nodes_yaml)
# reconvert network_ids to dict lost to string in rendering ...
for node in nodes_settings['nodes']:
    node['network_ids'] = ast.literal_eval(node['network_ids'])
pprint.pprint(nodes_settings)
resources = []

project_defaults = {
    "resources": [
#        {
#            "name": settings['node_prefix'],
#        },
    ],
    "sites": [
        {
            "site": os.environ['SITE'],
            "project": settings['os_tenant_name'],
            "username": settings['os_username'],
            "password": settings['os_password'],
            "keypair": settings['ssh_key_name'],
            "networks": settings['network_names'],
            "region": "",
        },
    ],
}

novaclient = os_novaclient.Client(settings['os_username'],
                                  settings['os_password'],
                                  settings['os_tenant_name'],
                                  settings['os_auth_url'],
                                  service_type='compute')
for node_settings in nodes_settings['nodes']:
    resource_settings = {}
    metadata = {}
    for key in ('flavor_id', 'image_id'):
        image = ""
        flavor = ""
        value = node_settings[key]
        if key == "image_id":
            image = novaclient.images.find(id=value)
            resource_settings["image"] = image.name
        elif key == "flavor_id":
            flavor = novaclient.flavors.find(id=str(value))
            resource_settings['flavor'] = flavor.name

    resource_settings['name'] = "rdo-ci"
    #resource_settings[key] = valye

    resource_settings['count'] = 1
    resource_settings['metadata'] = node_settings

    resources.append(resource_settings)

resources_to_provision = {'resources': resources}

# Generate nodes.yml
with open("nodes.yml", "w") as nodes_file:
    nodes_file.write(yaml.safe_dump(nodes_settings))

with open(args.resources_filename, "w") as resources_file:
    json.dump(resources_to_provision, resources_file, indent=4)

with open(project_defaults_filename, "w") as project_defaults_file:
    json.dump(project_defaults, project_defaults_file, indent=4)

with open(env_inject_filename, "w") as env_inject_file:
    # ci central ops adds .json at the end of this arguments value ...
    env_inject_file.write('COCP_PROJECT_DEFAULTS=%s\n' % (project_defaults_filename.replace(".json","")))
    env_inject_file.write('COCP_TOPOLOGY_PATH=%s\n' % (args.resources_filename.replace(".json","")))
    env_inject_file.write('COCP_NODE_PREFIX=%s\n' % (settings['node_prefix']))
    env_inject_file.write('COCP_KEY_FILE=%s\n' % (settings['ssh_private_key']))
