import os

import yaml

from yamlman import cli


YAML_PATH = './conf'


class Render(cli.Show):
    def take_action(self, parsed_args):
        return ''
