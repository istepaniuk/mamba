# -*- coding: utf-8 -*-

import os
import sys
import imp
import ast
import contextlib

from mamba import nodetransformers

class ExampleCollector(object):

    def __init__(self, paths):
        self.paths = paths

    def modules(self):
        for path in self._collect_files_containing_examples():
            with self._load_module_from(path) as module:
                yield module

    def _collect_files_containing_examples(self):
        collected = []
        for path in self.paths:
            if not os.path.exists(path):
                continue

            if os.path.isdir(path):
                collected.extend(self._collect_files_in_directory(path))
            else:
                collected.append(path)
        return collected


    def _collect_files_in_directory(self, directory):
        collected = []
        for root, dirs, files in os.walk(directory):
            collected.extend([os.path.join(self._normalize_path(root), file_)
                    for file_ in files if file_.endswith('_spec.py')])
        collected.sort()
        return collected

    def _normalize_path(self, path):
        return os.path.normpath(path)

    #TODO: What about managing locks with threads??
    #Take care with watchdog stuff!!
    @contextlib.contextmanager
    def _load_module_from(self, path):
        with open(path) as f:
            tree = ast.parse(f.read(), filename=path)
            tree = nodetransformers.TransformToSpecsNodeTransformer().visit(tree)
            ast.fix_missing_locations(tree)

        name = path.replace('.py', '')
        package = '.'.join(name.split('/')[:-1])

        try:
            module = imp.new_module(name)
            module.__package__ = package
            module.__file__ = path

            __import__(package)
            sys.modules[name] = module

            code = compile(tree, path, 'exec')
            exec(code, module.__dict__)

            yield module
        finally:
            if name in sys.modules:
                del sys.modules[name]

