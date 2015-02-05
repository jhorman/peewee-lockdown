from __future__ import absolute_import
from contextlib import contextmanager
import threading
from peewee import Param


class Context(threading.local):
    role = None
    transaction_depth = 0

    def get_rules(self, model_class):
        return self.role.get_rules(model_class) if self.role else []

    @contextmanager
    def transaction(self):
        self.transaction_depth += 1
        try:
            yield
        finally:
            self.transaction_depth -= 1


context = Context()


class ContextParam(Param):
    def __init__(self, context_var):
        super(ContextParam, self).__init__(None, None)
        self.context_var = context_var

    def __getattribute__(self, name):
        if name == 'value':
            return getattr(context, self.context_var, None)
        else:
            return super(ContextParam, self).__getattribute__(name)