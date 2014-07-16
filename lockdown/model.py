from __future__ import absolute_import

import peewee
from lockdown import LockdownException

from lockdown.context import context
from lockdown.rules import NO_ONE, EVERYONE


class SecureModel(peewee.Model):
    def is_readable(self, all_rules=None):
        if all_rules is None:
            all_rules = context.get_rules(self.__class__)

        for rules in all_rules:
            if rules.read_rule and not check_rule_expr(self, rules.read_rule):
                return False

        return True

    def is_field_readable(self, field, all_rules=None):
        if all_rules is None:
            all_rules = context.get_rules(self.__class__)

        if not self.is_readable(all_rules):
            return False

        for rules in all_rules:
            field_rules = rules.field_read_rules.get(field.name)
            if field_rules and not check_rule_expr(self, field_rules):
                return False

        return True

    def is_writable(self, all_rules=None):
        if all_rules is None:
            all_rules = context.get_rules(self.__class__)

        if not self.is_readable(all_rules):
            return False

        for rules in all_rules:
            if rules.write_rule and not check_rule_expr(self, rules.write_rule):
                return False
        return True

    def is_field_writeable(self, field, all_rules=None):
        if all_rules is None:
            all_rules = context.get_rules(self.__class__)

        if not self.is_writable(all_rules) or not self.is_field_readable(field, all_rules):
            return False

        for rules in all_rules:
            field_rules = rules.field_write_rules.get(field.name)
            if field_rules and not check_rule_expr(self, field_rules):
                return False

        return True

    def is_deleteable(self, all_rules=None):
        if all_rules is None:
            all_rules = context.get_rules(self.__class__)

        if not self.is_writable(all_rules):
            return False

        for rules in all_rules:
            if rules.delete_rule and not check_rule_expr(self, rules.delete_rule):
                return False

        return True

    @classmethod
    def select(cls, *selection):
        query = super(SecureModel, cls).select(*selection)
        all_rules = context.get_rules(cls)
        for rules in all_rules:
            if rules.read_rule:
                query = query.where(rules.read_rule)
        return query

    def save(self, force_insert=False, only=None):
        all_rules = context.get_rules(self.__class__)

        if not self.is_writable(all_rules):
            raise LockdownException('Model not writable in current context')

        if all_rules:
            fields_to_check = self._meta.get_fields() if only is None else only
            only = []
            for field in fields_to_check:
                if self.is_field_writeable(field, all_rules):
                    append_field = True
                    for rules in all_rules:
                        validation_fn = rules.field_validation.get(field.name)
                        if validation_fn:
                            value = getattr(self, field.name, None)
                            if not validation_fn(self, field, value):
                                append_field = False
                                break

                    if append_field:
                        only.append(field)

        return super(SecureModel, self).save(force_insert, only)

    def prepared(self):
        super(SecureModel, self).prepared()

        all_rules = context.get_rules(self.__class__)
        if all_rules:
            if not self.is_readable(all_rules):
                raise LockdownException('Model not readable in current context')

            for field in self._meta.get_fields():
                if field.name in self._data and not self.is_field_readable(field, all_rules):
                    del self._data[field.name]

    def delete_instance(self, recursive=False, delete_nullable=False):
        if not self.is_deleteable():
            raise LockdownException('Model not deletable in current context')
        return super(SecureModel, self).delete_instance(recursive, delete_nullable)


def check_rule_expr(instance, rule):
    if rule is NO_ONE:
        return False
    elif rule is EVERYONE:
        return True
    elif hasattr(rule, '__call__'):
        return rule(instance)
    else:
        return compare_left_right(getattr(instance, rule.lhs.name), rule.rhs)


def compare_left_right(lhs, rhs):
    if isinstance(lhs, peewee.Model):
        lhs = lhs.id
    if isinstance(rhs, peewee.Model):
        rhs = rhs.id
    if isinstance(rhs, peewee.Param):
        rhs = rhs.value
    return lhs == rhs