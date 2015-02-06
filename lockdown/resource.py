from __future__ import absolute_import

from flask.ext.peewee.rest import RestResource
from lockdown import LockdownException
from lockdown.context import lockdown_context
from lockdown.model import SecureModel


class SecureRestResource(RestResource):
    def check_get(self, obj=None):
        if obj is not None:
            return obj.is_readable()
        return super(SecureRestResource, self).check_get(obj)

    def check_put(self, obj):
        return self.check_post(obj)

    def check_post(self, obj=None):
        if obj is not None:
            return obj.is_writeable()
        return super(SecureRestResource, self).check_post(obj)

    def check_delete(self, obj):
        if obj:
            return obj.is_deleteable()
        return super(SecureRestResource, self).check_delete(obj)

    def prepare_data(self, obj, data):
        # remove any fields that are read-only in the current context
        # the data may have already been removed when the object was fetched,
        # but it could have been fetched in a different context, so re-filter.
        all_rules = lockdown_context.get_rules(self.model)
        if all_rules:
            for k in data:
                field = self.model._meta.fields.get(k)
                if field and not obj.is_field_readable(field, all_rules):
                    del data[k]

        return data

    def deserialize_object(self, data, instance):
        all_rules = lockdown_context.get_rules(self.model)
        if all_rules:
            # check if the api should be allowed to create an instance
            if instance is None or instance.get_id() is None and not SecureModel.is_creatable(all_rules):
                raise LockdownException('Model not creatable in current context')

            # check if api should be able to edit this instance
            if instance and not instance.is_writable(all_rules):
                raise LockdownException('Model not writable in current context')

            # remove any non-writable data
            writeable_data = {}
            for k, v in data.items():
                field = self.model._meta.fields.get(k)
                if not field or instance.is_field_writeable(instance, field, all_rules):
                    writeable_data[k] = v
            data = writeable_data

        return super(SecureRestResource, self).deserialize_object(data, instance)
