import copy
import fnmatch
import io
import itertools
import json
import logging

import yaml

from errors import YamlManException
from formatter import deep_format

logger = logging.getLogger(__name__)


def matches(what, glob_patterns):
    """
    Checks if the given string, ``what``, matches any of the glob patterns in
    the iterable, ``glob_patterns``

    :arg str what: String that we want to test if it matches a pattern
    :arg iterable glob_patterns: glob patterns to match (list, tuple, set,
    etc.)
    """
    return any(fnmatch.fnmatch(what, glob_pattern)
               for glob_pattern in glob_patterns)


class YamlParser(object):
    def __init__(self):
        self.data = {}
        self.objs = []
        self.path = ["./conf"]

    def parse_fp(self, fp):
        # wrap provided file streams to ensure correct encoding used
        data = yaml.safe_load(fp)
        if data:
            if not isinstance(data, list):
                raise YamlManException(
                    "The topmost collection in file '{fname}' must be a list,"
                    " not a {cls}".format(fname=getattr(fp, 'name', fp),
                                          cls=type(data)))
            for item in data:
                cls, dfn = next(iter(item.items()))
                group = self.data.get(cls, {})
                if len(item.items()) > 1:
                    n = None
                    for k, v in item.items():
                        if k == "name":
                            n = v
                            break
                    # Syntax error
                    raise YamlManException("Syntax error, for item "
                                               "named '{0}'. Missing indent?"
                                           .format(n))
                # allow any entry to specify an id that can also be used
                id = dfn['name']
                if id in group:
                    self._handle_dups(
                        "Duplicate entry found in '{0}: '{1}' already "
                        "defined".format(fp.name, id))
                group[id] = dfn
                self.data[cls] = group

    def parse(self, fn):
        with io.open(fn, 'r', encoding='utf-8') as fp:
            self.parse_fp(fp)

    def _handle_dups(self, message):
        logger.error(message)
        raise YamlManException(message)

    def getObj(self, name):
        return self.data.get('obj', {}).get(name, None)

    def getTemplate(self, name):
        return self.data.get('template', {}).get(name, None)

    def applyDefaults(self, data, override_dict=None):
        if override_dict is None:
            override_dict = {}

        whichdefaults = data.get('defaults', 'global')
        defaults = copy.deepcopy(self.data.get('defaults',
                                 {}).get(whichdefaults, {}))
        if defaults == {} and whichdefaults != 'global':
            raise YamlManException("Unknown defaults set: '{0}'"
                                   .format(whichdefaults))

        for key in override_dict.keys():
            if key in defaults.keys():
                defaults[key] = override_dict[key]

        newdata = {}
        newdata.update(defaults)
        newdata.update(data)
        return newdata

    def expandYaml(self, objs_glob=None):
        for obj in self.data.get('obj', {}).values():
            if objs_glob and not matches(obj['name'], objs_glob):
                logger.debug("Ignoring obj {0}".format(obj['name']))
                continue
            logger.debug("Expanding obj '{0}'".format(obj['name']))
            self.objs.append(obj)
        for project in self.data.get('project', {}).values():
            # use a set to check for duplicate job references in projects
            seen = set()
            for objspec in project.get('objs', []):
                if isinstance(objspec, dict):
                    # Singleton dict containing dict of job-specific params
                    objname, objparams = next(iter(objspec.items()))
                    if not isinstance(objparams, dict):
                        objparams = {}
                else:
                    objname = objspec
                    objparams = {}
                obj = self.getObj(objname)
                if obj:
                    # Just naming an existing defined job
                    if objname in seen:
                        self._handle_dups("Duplicate obj '{0}' specified "
                                          "for project '{1}'".format(
                                              objname, project['name']))
                    seen.add(objname)
                    continue
                 # see if it's a template
                template = self.getTemplate(objname)
                if template:
                    d = {}
                    d.update(project)
                    d.update(objparams)
                    self.expandYamlForTemplate(d, template, objs_glob)
                else:
                    raise YamlManException("Failed to find suitable "
                                               "template named '{0}'"
                                           .format(objname))
        # check for duplicate generated jobs
        seen = set()
        # walk the list in reverse so that last definition wins
        for obj in self.objs[::-1]:
            if obj['name'] in seen:
                self._handle_dups("Duplicate definitions for job '{0}' "
                                  "specified".format(obj['name']))
                self.objs.remove(obj)
            seen.add(obj['name'])

    def expandYamlForTemplate(self, project, template, objs_glob=None):
        dimensions = []
        template_name = template['name']
        # reject keys that are not useful during yaml expansion
        for k in ['objs']:
            project.pop(k)
        for (k, v) in project.items():
            tmpk = '{{{0}}}'.format(k)
            if tmpk not in template_name:
                continue
            if type(v) == list:
                dimensions.append(zip([k] * len(v), v))
        # XXX somewhat hackish to ensure we actually have a single
        # pass through the loop
        if len(dimensions) == 0:
            dimensions = [(("", ""),)]

        for values in itertools.product(*dimensions):
            params = copy.deepcopy(project)
            params = self.applyDefaults(params, template)

            expanded_values = {}
            for (k, v) in values:
                if isinstance(v, dict):
                    inner_key = next(iter(v))
                    expanded_values[k] = inner_key
                    expanded_values.update(v[inner_key])
                else:
                    expanded_values[k] = v

            params.update(expanded_values)
            params = deep_format(params, params)

            for key in template.keys():
                if key not in params:
                    params[key] = template[key]

            for k, v in template.iteritems():
                if k in project and k != 'name':
                    template[k] = project[k]

            params['template-name'] = template_name
            expanded = deep_format(template, params)

            job_name = expanded.get('name')
            if objs_glob and not matches(job_name, objs_glob):
                continue

            self.objs.append(expanded)

    def renderYaml(self):
        self.objs = [self._render_obj(obj)[1] for obj in self.objs]
        print json.dumps(self.objs)

    def _render_obj(self, obj):
        is_macro = False
        if isinstance(obj, list):
            ret = type(obj)()
            for item in obj:
                im, reti = self._render_obj(item)
                if im and isinstance(reti, list):
                    for itemi in reti:
                        ret.append(itemi)
                else:
                    ret.append(reti)
        elif isinstance(obj, dict):
            name, macro_args = next(iter(obj.items()))
            macro = self.data.get('macro', {}).get(name)
            if macro:
                is_macro = True
                ret = self._render_macro(macro, macro_args)
            else:
                ret = type(obj)()
                for k, v in obj.iteritems():
                    im, reti = self._render_obj(v)
                    if im and isinstance(reti, list):
                        ret[k] = type(reti)()
                        for item in reti:
                            ret[k].append(item)
                    else:
                        ret[k] = reti
        else:
            name = obj
            macro_args = {}
            macro = self.data.get('macro', {}).get(name)
            if macro:
                is_macro = True
                ret = self._render_macro(macro, macro_args)
            else:
                ret = obj
        return is_macro, ret

    def _render_macro(self, macro, macro_args):
        if 'name' in macro:
            macro.pop('name')
        m, m_data = next(iter(macro.items()))
        _, ret = self._render_obj(deep_format(m_data, macro_args))
        return ret
