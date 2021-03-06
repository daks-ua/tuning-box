# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import

from cliff import command
from fuelclient import client as fc_client

from tuning_box import cli
from tuning_box.cli import base as cli_base
from tuning_box.cli import components
from tuning_box.cli import environments
from tuning_box.cli import resource_definitions
from tuning_box.cli import resources
from tuning_box import client as tb_client


class FuelHTTPClient(tb_client.HTTPClient):
    if hasattr(fc_client, 'DefaultAPIClient'):
        # Handling python-fuelclient version >= 10.0
        fc_api = fc_client.DefaultAPIClient
    else:
        # Handling python-fuelclient version <= 9.0
        fc_api = fc_client.APIClient

    def __init__(self):
        service_catalog = self.fc_api.keystone_client.service_catalog
        base_url = service_catalog.url_for(
            service_type='config',
            endpoint_type='publicURL',
        )
        super(FuelHTTPClient, self).__init__(base_url)

    def default_headers(self):
        headers = super(FuelHTTPClient, self).default_headers()
        if self.fc_api.auth_token:
            headers['X-Auth-Token'] = self.fc_api.auth_token
        return headers


class FuelBaseCommand(cli_base.BaseCommand):
    def get_client(self):
        return FuelHTTPClient()


class Get(FuelBaseCommand, resources.Get):
    pass


class Set(FuelBaseCommand, resources.Set):
    pass


class Delete(FuelBaseCommand, resources.Delete):
    pass


class Override(FuelBaseCommand, resources.Override):
    pass


class DeleteOverride(FuelBaseCommand, resources.DeleteOverride):
    pass


class CreateEnvironment(FuelBaseCommand, environments.CreateEnvironment):
    pass


class ListEnvironments(FuelBaseCommand, environments.ListEnvironments):
    pass


class ShowEnvironment(FuelBaseCommand, environments.ShowEnvironment):
    pass


class DeleteEnvironment(FuelBaseCommand, environments.DeleteEnvironment):
    pass


class UpdateEnvironment(FuelBaseCommand, environments.UpdateEnvironment):
    pass


class CreateComponent(FuelBaseCommand, components.CreateComponent):
    pass


class ListComponents(FuelBaseCommand, components.ListComponents):
    pass


class ShowComponent(FuelBaseCommand, components.ShowComponent):
    pass


class DeleteComponent(FuelBaseCommand, components.DeleteComponent):
    pass


class UpdateComponent(FuelBaseCommand, components.UpdateComponent):
    pass


class CreateResourceDefinition(
    FuelBaseCommand,
    resource_definitions.CreateResourceDefinition
):
    pass


class ListResourceDefinitions(
    FuelBaseCommand,
    resource_definitions.ListResourceDefinitions
):
    pass


class ShowResourceDefinition(
    FuelBaseCommand,
    resource_definitions.ShowResourceDefinition
):
    pass


class DeleteResourceDefinition(
    FuelBaseCommand,
    resource_definitions.DeleteResourceDefinition
):
    pass


class UpdateResourceDefinition(
    FuelBaseCommand,
    resource_definitions.UpdateResourceDefinition
):
    pass


class Config(command.Command):
    def get_parser(self, *args, **kwargs):
        parser = super(Config, self).get_parser(*args, **kwargs)
        parser.add_argument('args', nargs='*')
        return parser

    def take_action(self, parsed_args):
        client = FuelHTTPClient()
        app = cli.TuningBoxApp(client)
        app.run(parsed_args.args)
