from __future__ import absolute_import


class Rules(object):
    def __init__(self, model_class):
        super(Rules, self).__init__()
        self.model_class = model_class
        self.read_rule = None
        self.field_read_rules = {}
        self.write_rule = None
        self.field_write_rules = {}

    def readable_by(self, expr):
        self.read_rule = expr
        return self

    def field_readable_by(self, field, expr):
        self.field_read_rules[field] = expr
        return self

    def writeable_by(self, expr):
        self.write_rule = expr
        return self

    def field_writeable_by(self, field, expr):
        self.field_write_rules[field] = expr
        return self

