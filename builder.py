import logging
import os
import time

from parser import YamlParser

logger = logging.getLogger(__name__)


class Builder(object):
    def __init__(self):
        pass

    def load_files(self, fn):
        self.parser = YamlParser()

        # handle deprecated behavior, and check that it's not a file like
        # object as these may implement the '__iter__' attribute.
        if not hasattr(fn, '__iter__') or hasattr(fn, 'read'):
            logger.warning(
                'Passing single elements for the `fn` argument in '
                'Builder.load_files is deprecated. Please update your code '
                'to use a list as support for automatic conversion will be '
                'removed in a future version.')
            fn = [fn]

        files_to_process = []
        for path in fn:
            if not hasattr(path, 'read') and os.path.isdir(path):
                files_to_process.extend([os.path.join(path, f)
                                         for f in os.listdir(path)
                                         if (f.endswith('.yml')
                                             or f.endswith('.yaml'))])
            else:
                files_to_process.append(path)

        # symlinks used to allow loading of sub-dirs can result in duplicate
        # definitions of macros and templates when loading all from top-level
        unique_files = []
        for f in files_to_process:
            if hasattr(f, 'read'):
                unique_files.append(f)
                continue
            rpf = os.path.realpath(f)
            if rpf not in unique_files:
                unique_files.append(rpf)
            else:
                logger.warning("File '%s' already added as '%s', ignoring "
                               "reference to avoid duplicating yaml "
                               "definitions." % (f, rpf))

        print unique_files

        for in_file in unique_files:
            # use of ask-for-permissions instead of ask-for-forgiveness
            # performs better when low use cases.
            if hasattr(in_file, 'name'):
                fname = in_file.name
            else:
                fname = in_file
            logger.debug("Parsing YAML file {0}".format(fname))
            if hasattr(in_file, 'read'):
                self.parser.parse_fp(in_file)
            else:
                self.parser.parse(in_file)

    def update_objs(self, input_fn, objs_glob=None):
        orig = time.time()
        self.load_files(input_fn)
        self.parser.expandYaml(objs_glob)
        self.parser.renderYaml()
        step = time.time()
        logging.debug('%d XML files generated in %ss',
                      len(self.parser.objs), str(step - orig))


if __name__ == '__main__':
    Builder().update_objs('./conf')
