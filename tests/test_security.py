from __future__ import absolute_import

from playhouse.test_utils import test_database
from lockdown import Role
from lockdown.context import ContextParam, context
from lockdown.rules import NO_ONE
from tests import test_db, Bicycle, User, Group


def test_select_security():
    context.role = None
    context.user = None
    context.group = None

    rest_api = Role('rest_api')
    rest_api.lockdown(Bicycle).readable_by(Bicycle.group == ContextParam('group'))

    sql, params = Bicycle.select().sql()
    assert '"group_id" = ?' not in sql
    assert len(params) == 0

    context.role = rest_api
    context.group = 10
    context.user = 10

    sql, params = Bicycle.select().sql()
    assert '"group_id" = ?' in sql
    assert params[0] == 10


def test_readable_writable():
    context.role = None
    context.user = None
    context.group = None

    rest_api = Role('rest_api')
    ldown = rest_api.lockdown(Bicycle) \
        .readable_by(Bicycle.group == ContextParam('group')) \
        .writeable_by(Bicycle.owner == ContextParam('user'))

    with test_database(test_db, [User, Group, Bicycle]):
        u = User.create(username='test')
        g = Group.create(name='test')
        b = Bicycle.create(owner=u, group=g)

        assert b.is_readable() is True
        assert b.is_writable() is True

        context.role = rest_api

        assert b.is_readable() is False
        assert b.is_writable() is False

        context.group = 10
        context.user = 10

        assert b.is_readable() is False
        assert b.is_writable() is False

        context.group = g.id

        assert b.is_readable() is True
        assert b.is_writable() is False

        context.user = u.id

        assert b.is_readable() is True
        assert b.is_writable() is True


def test_is_readable_writable_field():
    context.role = None
    context.user = None
    context.group = None

    rest_api = Role('rest_api')
    rest_api.lockdown(Bicycle) \
        .field_readable_by(Bicycle.serial, Bicycle.group == ContextParam('group')) \
        .field_writeable_by(Bicycle.serial, Bicycle.owner == ContextParam('user'))

    with test_database(test_db, [User, Group, Bicycle]):
        u = User.create(username='test')
        g = Group.create(name='test')
        b = Bicycle.create(owner=u, group=g)

        context.role = rest_api

        assert b.is_field_readable(Bicycle.serial) is False
        assert b.is_field_writeable(Bicycle.serial) is False

        context.group = 10
        context.user = 10

        assert b.is_field_readable(Bicycle.serial) is False
        assert b.is_field_writeable(Bicycle.serial) is False

        context.group = g.id

        assert b.is_field_readable(Bicycle.serial) is True
        assert b.is_field_writeable(Bicycle.serial) is False

        context.user = u.id

        assert b.is_field_readable(Bicycle.serial) is True
        assert b.is_field_writeable(Bicycle.serial) is True


def test_save():
    context.role = None
    context.user = None
    context.group = None

    rest_api = Role('rest_api')
    rest_api.lockdown(Bicycle) \
        .field_readable_by(Bicycle.serial, Bicycle.group == ContextParam('group')) \
        .field_writeable_by(Bicycle.serial, Bicycle.owner == ContextParam('user'))

    with test_database(test_db, [User, Group, Bicycle]):
        u = User.create(username='test')
        g = Group.create(name='test')
        b = Bicycle.create(owner=u, group=g, serial='1')

        context.role = rest_api

        b.serial = '10'
        b.save()

        assert b.serial == '10'
        b = Bicycle.get()
        assert b.serial is None, 'cant read this field, no group'

        context.group = g.id

        b = Bicycle.get()
        assert b.serial == '1', 'now this field can be read, should be 1 still'

        context.user = u.id

        b.serial = '10'
        b.save()
        b = Bicycle.get()
        assert b.serial == '10'


def test_no_one():
    context.role = None
    context.user = None
    context.group = None

    rest_api = Role('rest_api')
    rest_api.lockdown(Bicycle).readable_by(NO_ONE).writeable_by(NO_ONE)


    with test_database(test_db, [User, Group, Bicycle]):
        u = User.create(username='test')
        g = Group.create(name='test')
        b = Bicycle.create(owner=u, group=g)

        context.role = rest_api

        assert b.is_readable() is False
        assert b.is_writable() is False

        context.group = g.id
        context.user = u.id

        assert b.is_readable() is False
        assert b.is_writable() is False
