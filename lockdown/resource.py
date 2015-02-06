from __future__ import absolute_import

from flask.ext.peewee.rest import RestResource
from lockdown.context import lockdown_context


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

    def deserialize_object(self, data, instance):
        all_rules = lockdown_context.get_rules(self.model)
        if all_rules:
            writeable_data = {}
            for k, v in data.items():
                field = self.model._meta.fields.get(k)
                if not field or instance.is_field_writeable(instance, field, all_rules):
                    writeable_data[k] = v
            data = writeable_data
        return super(SecureRestResource, self).deserialize_object(data, instance)
