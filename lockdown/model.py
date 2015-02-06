from __future__ import absolute_import
from peewee import Param, SelectQuery, Field

from playhouse.signals import Model
from lockdown import LockdownException
from lockdown.context import lockdown_context
from lockdown.rules import NO_ONE, EVERYONE


class SecureModel(Model):
    def __init__(self, *args, **kwargs):
        self._secure_data = {}
        self._change_contexts = {}
        super(SecureModel, self).__init__(*args, **kwargs)

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

    @classmethod
    def is_creatable(cls, all_rules=None):
        if all_rules is None:
            all_rules = lockdown_context.get_rules(cls)

        for rules in all_rules:
            if rules.create_rule and not check_rule_expr(None, rules.create_rule):
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
            return resolve(self, value) == resolve(self, validation_expr.rhs)

    def __setattr__(self, key, value):
        field = self._meta.fields.get(key)

        if field:
            # if the object doesn't yet have an id, and this is the id field
            # turn off validation. this ensures that peewee queries aren't
            # self validating since the first field a query will fill is id.
            # once the query is complete, prepared will turn validation back on
            if not self.get_id() and field.primary_key:
                self._validate = False

            # if validation is enabled check that the field is writable
            if getattr(self, '_validate', True):
                all_rules = lockdown_context.get_rules(self.__class__)
                self.check_field_writable(all_rules, field, value, True)

            # capture the role doing the setting. this lets different fields
            # get set by different contexts
            if lockdown_context.role:
                self._change_contexts[key] = lockdown_context.role

        return super(SecureModel, self).__setattr__(key, value)

    def save(self, force_insert=False, only=None):
        all_rules = lockdown_context.get_rules(self.__class__)

        if self.get_id() is None and not self.is_creatable(all_rules):
            raise LockdownException('Model not creatable in current context')

        if not self.is_writable(all_rules):
            raise LockdownException('Model not writable in current context')

        if all_rules:
            fields_to_check = self._meta.get_fields() if only is None else only
            only = []
            for field in fields_to_check:
                value = getattr(self, field.name) if field.name in self._data else None
                # check if this field has a change context set. if so that means
                # setattr already validated the change and it can just be accepted here.
                # this is useful so one context can set some fields, then maybe a server
                # context could set a field like `modified`.
                change_context = self._change_contexts.get(field.name)
                if change_context or self.check_field_writable(all_rules, field, value, False):
                    only.append(field)

        return super(SecureModel, self).save(force_insert, only)

    def prepared(self):
        super(SecureModel, self).prepared()
        self._validate = True

        all_rules = lockdown_context.get_rules(self.__class__)
        if all_rules:
            if not self.is_readable(all_rules):
                raise LockdownException('Model not readable in current context')

            to_remove = []
            for field in self._meta.get_fields():
                if field.name in self._data and not self.is_field_readable(field, all_rules):
                    to_remove.append(field.name)

            if to_remove:
                # make a backup of the raw data so it could still be accessed for things like caching
                self._secure_data = dict(self._data)
                # remove the fields that are not visible
                for field_name in to_remove:
                    del self._data[field_name]

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
        if rule.op == 'and':
            return check_rule_expr(instance, rule.lhs) and check_rule_expr(instance, rule.rhs)
        elif rule.op == 'or':
            return check_rule_expr(instance, rule.lhs) or check_rule_expr(instance, rule.rhs)
        elif rule.op == 'in':
            lhs_value = resolve(instance, rule.lhs)
            list = [resolve(instance, item) for item in rule.rhs]
            return lhs_value in list
        else:
            lhs_value = resolve(instance, rule.lhs)
            rhs_value = resolve(instance, rule.rhs)

            # special case null. this is to handle for example, when a object is being
            # created and owner is still null, and so owner can't be used to validate
            if (isinstance(rule.lhs, Field) and lhs_value is None) or \
                    (isinstance(rule.rhs, Field) and rhs_value is None):
                return True

            return lhs_value == rhs_value


def resolve(instance, value):
    if isinstance(value, Field):
        return resolve(instance, getattr(instance, value.name) if value.name in instance._data else None)
    if isinstance(value, Model):
        return value.id
    if isinstance(value, Param):
        return resolve(instance, value.value)
    return value
