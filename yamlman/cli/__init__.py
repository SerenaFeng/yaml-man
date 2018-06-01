import abc
import logging

from cliff import command
from cliff import lister
import six
import os


def get_item_properties(item, fields):
    """Return a tuple containing the item properties.

    :param item: a single item resource (e.g. Server, Project, etc)
    :param fields: tuple of strings with the desired field names
    """

    return tuple([item.get(field, '') for field in fields])


class CommandMeta(abc.ABCMeta):

    def __new__(mcs, name, bases, cls_dict):
        if 'log' not in cls_dict:
            cls_dict['log'] = logging.getLogger(
                cls_dict['__module__'] + '.' + name)
        return super(CommandMeta, mcs).__new__(mcs, name, bases, cls_dict)


@six.add_metaclass(CommandMeta)
class Command(command.Command):
    def run(self, parsed_args):
        self.log.debug('run(%s)', parsed_args)
        return super(Command, self).run(parsed_args)

class Lister(Command, lister.Lister):
    @staticmethod
    def format_output(columns, data):
        return (columns,
                (get_item_properties(s, columns) for s in data))


class Show(Command):
    @staticmethod
    def format_output(columns, data):
        return (columns,
                (get_item_properties(s, columns) for s in data))

    def read_file(self, name):
        file = self.get_file(name)
        if os.path.isfile(file):
            with open(file, 'r') as fd:
                try:
                    print fd.read()
                except Exception as exc:
                    print exc
        else:
            self.log.error('{} not supported'.format(name))
