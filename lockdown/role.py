from __future__ import absolute_import
from lockdown.rules import Rules


class Role(object):
    def __init__(self, name, from_roles=None):
        super(Role, self).__init__()
        self.name = name
        self.from_roles = from_roles or []
        self.rules = {}

    def extend(self, name):
        return Role(name, [self])

    def lockdown(self, model_class):
        rules = Rules(model_class)
        self.rules[model_class] = rules
        return rules

    def get_rules(self, model_class):
        return self.collect_rules(model_class, [])

    def collect_rules(self, model_class, list):
        for role in self.from_roles:
            role.collect_rules(model_class, list)
        rules = self.rules.get(model_class)
        if rules:
            list.append(rules)
        if model_class.__base__:
            self.collect_rules(model_class.__base__, list)
        return list

