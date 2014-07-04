from __future__ import absolute_import

import peewee

from lockdown.context import context


class SecureModel(peewee.Model):
    def is_readable(self):
        rules = context.get_rules(self.__class__)
        if rules and rules.read_rule:
            return check_rule_expr(self, rules.read_rule)
        return True

    def is_field_readable(self, field):
        if self.is_readable():
            rules = context.get_rules(self.__class__)
            if rules:
                field_rules = rules.field_read_rules.get(field)
                if field_rules:
                    return check_rule_expr(self, field_rules)
            return True
        return False

    def is_writable(self):
        if self.is_readable():
            rules = context.get_rules(self.__class__)
            if rules and rules.write_rule:
                return check_rule_expr(self, rules.write_rule)
            return True
        return False

    def is_field_writeable(self, field):
        if self.is_field_readable(field) and self.is_writable():
            rules = context.get_rules(self.__class__)
            if rules:
                field_rules = rules.field_write_rules.get(field)
                if field_rules:
                    return check_rule_expr(self, field_rules)
            return True
        return False

    @classmethod
    def select(cls, *selection):
        query = super(SecureModel, cls).select(*selection)
        lockdown = context.get_rules(cls)
        if lockdown:
            query = query.where(lockdown.read_rule)
        return query

    def save(self, force_insert=False, only=None):
        rules = context.get_rules(self.__class__)
        if rules:
            if only is None:
                only = []
            for field in self._meta.get_fields():
                if self.is_field_writeable(field):
                    only.append(field)
        return super(SecureModel, self).save(force_insert, only)

    def prepared(self):
        super(SecureModel, self).prepared()
        rules = context.get_rules(self.__class__)
        if rules:
            for field in self._meta.get_fields():
                if field.name in self._data and not self.is_field_readable(field):
                    del self._data[field.name]


def check_rule_expr(instance, rule):
    return compare_left_right(getattr(instance, rule.lhs.name), rule.rhs)


def compare_left_right(lhs, rhs):
    if isinstance(lhs, peewee.Model):
        lhs = lhs.id
    if isinstance(rhs, peewee.Model):
        rhs = rhs.id
    if isinstance(rhs, peewee.Param):
        rhs = rhs.value
    return lhs == rhs