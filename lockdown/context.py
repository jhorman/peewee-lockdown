from __future__ import absolute_import
from contextlib import contextmanager
import threading
from peewee import Param


class LockdownContext(threading.local):
    role = None
    transaction_depth = 0

    def get_rules(self, model_class):
        return self.role.get_rules(model_class) if self.role else []

    def reset(self):
        self.role = None
        self.transaction_depth = 0

    @contextmanager
    def as_role(self, role):
        old_role = self.role
        self.role = role
        try:
            yield
        finally:
            self.role = old_role

    @contextmanager
    def transaction(self):
        self.transaction_depth += 1
        try:
            yield
        finally:
            self.transaction_depth -= 1


lockdown_context = LockdownContext()


class ContextParam(Param):
    def __init__(self, context_var):
        super(ContextParam, self).__init__(None, None)
        self.context_var = context_var

    def __getattribute__(self, name):
        if name == 'value':
            return getattr(lockdown_context, self.context_var, None)
        else:
            return super(ContextParam, self).__getattribute__(name)