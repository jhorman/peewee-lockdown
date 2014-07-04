from __future__ import absolute_import

from flask.ext.peewee.rest import RestResource


class SecureRestResource(RestResource):
    def check_get(self, obj=None):
        if obj is not None:
            return obj.is_readable()
        return super(SecureRestResource, self).check_get(obj)

    def check_put(self, obj):
        if obj is not None:
            return obj.is_writeable()
        return super(SecureRestResource, self).check_put(obj)

    def check_post(self, obj=None):
        if obj is not None:
            return obj.is_writeable()
        return super(SecureRestResource, self).check_post(obj)

    def check_delete(self, obj):
        if obj:
            return obj.is_deleteable()
        return super(SecureRestResource, self).check_delete(obj)

    def deserialize_object(self, data, instance):
        writeable_data = {}
        for k, v in data.items():
            if instance.is_field_writeable(instance, k):
                writeable_data[k] = v
        return super(SecureRestResource, self).deserialize_object(writeable_data, instance)
