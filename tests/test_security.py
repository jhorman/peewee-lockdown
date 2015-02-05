from __future__ import absolute_import
from peewee import IntegrityError

from playhouse.test_utils import test_database
from lockdown import Role, LockdownException
from lockdown.context import ContextParam, context
from lockdown.rules import NO_ONE
from tests import test_db, Bicycle, User, Group, BaseModel


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

    rest_api.lockdown(BaseModel)\
        .field_writeable_by(BaseModel.created, NO_ONE)\
        .field_writeable_by(BaseModel.modified, NO_ONE)

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
        assert b.is_field_writeable(Bicycle.modified) is False
        assert b.is_field_writeable(Bicycle.created) is False

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


def test_insert():
    context.role = None
    context.user = None
    context.group = None

    rest_api = Role('rest_api')

    rest_api.lockdown(BaseModel)\
        .field_writeable_by(BaseModel.created, NO_ONE)\
        .field_writeable_by(BaseModel.modified, NO_ONE)

    rest_api.lockdown(Bicycle) \
        .field_writeable_by(Bicycle.owner, Bicycle.owner == ContextParam('user')) \
        .field_writeable_by(Bicycle.serial, Bicycle.owner == ContextParam('user'))

    with test_database(test_db, [User, Group, Bicycle]):
        u = User.create(username='test')
        g = Group.create(name='test')

        # set the role/user before inserting
        context.role = rest_api

        try:
            Bicycle.create(owner=u, group=g, serial='1')
            assert False, 'should have thrown since no user set'
        except IntegrityError:
            pass

        context.user = u.id

        # insert should work fine since object validates
        Bicycle.create(owner=u, group=g, serial='1')
        b = Bicycle.get()

        assert b.modified is not None
        assert b.created is not None
        assert b.serial == '1'
        assert b.owner == u
        assert b.group == g


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


def test_lockdown_user():
    context.role = None
    context.user = None
    context.group = None

    rest_api = Role('rest_api')
    rest_api.lockdown(Bicycle) \
        .field_writeable_by(Bicycle.owner, Bicycle.owner == ContextParam('user'))

    with test_database(test_db, [User, Group, Bicycle]):
        u = User.create(username='test')
        u2 = User.create(username='test2')
        g = Group.create(name='test')
        b = Bicycle.create(owner=u, group=g)

        context.role = rest_api

        assert b.is_field_writeable(Bicycle.owner) is False

        context.user = 10

        assert b.is_field_writeable(Bicycle.owner) is False
        b.owner = u2
        b.save()
        b = Bicycle.get()
        assert b.owner == u, 'shouldnt save the user change'

        context.user = u.id

        assert b.is_field_writeable(Bicycle.owner) is True

def test_transaction():
    rest_api = Role('rest_api')
    rest_api.lockdown(Bicycle).readable_by(NO_ONE).writeable_by(NO_ONE)

    with test_database(test_db, [User, Group, Bicycle]):
        u = User.create(username='test')
        u2 = User.create(username='test2')
        g = Group.create(name='test')
        b = Bicycle.create(owner=u, group=g)

        context.role = rest_api
        b.owner = u2

        with context.transaction():
            try:
                b.owner = u2
                assert False, 'should have thrown exception'
            except LockdownException:
                pass


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
