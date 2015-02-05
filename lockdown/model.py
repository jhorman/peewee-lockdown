from __future__ import absolute_import
from peewee import Param, SelectQuery

from playhouse.signals import Model
from lockdown import LockdownException
from lockdown.context import lockdown_context
from lockdown.rules import NO_ONE, EVERYONE


class SecureModel(Model):
    def is_readable(self, all_rules=None):
        if all_rules is None:
            all_rules = lockdown_context.get_rules(self.__class__)

        for rules in all_rules:
            if rules.read_rule and not check_rule_expr(self, rules.read_rule):
                return False

        return True

    def is_field_readable(self, field, all_rules=None):
        if all_rules is None:
            all_rules = lockdown_context.get_rules(self.__class__)

        if not self.is_readable(all_rules):
            return False

        for rules in all_rules:
            field_rules = rules.field_read_rules.get(field.name)
            if field_rules and not check_rule_expr(self, field_rules):
                return False

        return True

    def is_writable(self, all_rules=None):
        if all_rules is None:
            all_rules = lockdown_context.get_rules(self.__class__)

        if not self.is_readable(all_rules):
            return False

        for rules in all_rules:
            if rules.write_rule and not check_rule_expr(self, rules.write_rule):
                return False
        return True

    def is_field_writeable(self, field, all_rules=None):
        if all_rules is None:
            all_rules = lockdown_context.get_rules(self.__class__)

        if not self.is_writable(all_rules) or not self.is_field_readable(field, all_rules):
            return False

        for rules in all_rules:
            field_rules = rules.field_write_rules.get(field.name)
            if field_rules and not check_rule_expr(self, field_rules):
                return False

        return True

    def is_deleteable(self, all_rules=None):
        if all_rules is None:
            all_rules = lockdown_context.get_rules(self.__class__)

        if not self.is_writable(all_rules):
            return False

        for rules in all_rules:
            if rules.delete_rule and not check_rule_expr(self, rules.delete_rule):
                return False

        return True

    @classmethod
    def select(cls, *selection):
        query = cls.create_select_query(*selection)
        all_rules = lockdown_context.get_rules(cls)
        for rules in all_rules:
            if rules.read_rule:
                query = query.where(rules.read_rule)
        if cls._meta.order_by:
            query = query.order_by(*cls._meta.order_by)
        return query

    @classmethod
    def create_select_query(cls, *selection):
        return SelectQuery(cls, *selection)

    def check_field_writable(self, all_rules, field, value, throw_exception):
        if not self.is_field_writeable(field, all_rules):
            if throw_exception:
                raise LockdownException('Field {name} not writable'.format(name=field.name))
            else:
                return False

        for rules in all_rules:
            validation_expr = rules.field_validation.get(field.name)
            if validation_expr:
                if not self.check_field_validation(validation_expr, field, value):
                    if throw_exception:
                        raise LockdownException('Validation error for field {name}'.format(name=field.name))
                    else:
                        return False

        return True

    def check_field_validation(self, validation_expr, field, value):
        if hasattr(validation_expr, '__call__'):
            return validation_expr(self, field, value)
        else:
            return compare_left_right(value, validation_expr.rhs)

    def __setattr__(self, key, value):
        if lockdown_context.transaction_depth > 0:
            field = self._meta.fields.get(key)
            if field:
                all_rules = lockdown_context.get_rules(self.__class__)
                self.check_field_writable(all_rules, field, value, True)

        return super(SecureModel, self).__setattr__(key, value)

    def save(self, force_insert=False, only=None):
        all_rules = lockdown_context.get_rules(self.__class__)

        if not self.is_writable(all_rules):
            raise LockdownException('Model not writable in current context')

        if all_rules:
            fields_to_check = self._meta.get_fields() if only is None else only
            only = []
            for field in fields_to_check:
                value = getattr(self, field.name, None)
                if self.check_field_writable(all_rules, field, value, False):
                    only.append(field)

        return super(SecureModel, self).save(force_insert, only)

    def prepared(self):
        super(SecureModel, self).prepared()

        all_rules = lockdown_context.get_rules(self.__class__)
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
    if isinstance(lhs, Model):
        lhs = lhs.id
    if isinstance(rhs, Model):
        rhs = rhs.id
    if isinstance(rhs, Param):
        rhs = rhs.value
    return lhs == rhs