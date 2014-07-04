from __future__ import absolute_import
from lockdown.rules import Rules


class Role(object):
    def __init__(self, name):
        super(Role, self).__init__()
        self.name = name
        self.rules = {}

    def lockdown(self, model_class):
        rules = Rules(model_class)
        self.rules[model_class] = rules
        return rules

    def get_rules(self, model_class):
        return self.rules.get(model_class)