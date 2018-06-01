import sys

from cliff import app
from cliff import commandmanager


class YamlProjectShell(app.App):

    def __init__(self):
        super(YamlProjectShell, self).__init__(
            description='docker-trigger cli',
            version='0.1',
            command_manager=commandmanager.CommandManager('ddr'),
            deferred_help=True,
        )

    def initialize_app(self, argv):
        self.LOG.debug('initialize_app')

    def prepare_to_run_command(self, cmd):
        self.LOG.debug('prepare_to_run_command %s', cmd.__class__.__name__)

    def clean_up(self, cmd, result, err):
        self.LOG.debug('clean_up %s', cmd.__class__.__name__)
        if err:
            self.LOG.debug('got an error: %s', err)


def main(argv=sys.argv[1:]):
    ddr = YamlProjectShell()
    return ddr.run(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
