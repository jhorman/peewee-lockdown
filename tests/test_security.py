from __future__ import absolute_import
from datetime import datetime
from nose import with_setup

from playhouse.test_utils import test_database
from lockdown import Role, LockdownException
from lockdown.context import ContextParam, lockdown_context
from lockdown.rules import NO_ONE
from tests import test_db, Bicycle, User, Group, BaseModel, BigWheel


def setup():
    lockdown_context.role = None
    lockdown_context.user = None
    lockdown_context.group = None
    lockdown_context.custom_role = None


@with_setup(setup)
def test_select_security():
    lockdown_context.role = None
    lockdown_context.user = None
    lockdown_context.group = None

    rest_api = Role('rest_api')
    rest_api.lockdown(Bicycle).readable_by(Bicycle.group == ContextParam('group'))

    sql, params = Bicycle.select().sql()
    assert '"group_id" = ?' not in sql
    assert len(params) == 0

    lockdown_context.role = rest_api
    lockdown_context.group = 10
    lockdown_context.user = 10

    sql, params = Bicycle.select().sql()
    assert '"group_id" = ?' in sql
    assert params[0] == 10


@with_setup(setup)
def test_readable_writable():
    lockdown_context.role = None
    lockdown_context.user = None
    lockdown_context.group = None

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

        lockdown_context.role = rest_api

        assert b.is_readable() is False
        assert b.is_writable() is False

        lockdown_context.group = 10
        lockdown_context.user = 10

        assert b.is_readable() is False
        assert b.is_writable() is False

        lockdown_context.group = g.id

        assert b.is_readable() is True
        assert b.is_writable() is False

        lockdown_context.user = u.id

        assert b.is_readable() is True
        assert b.is_writable() is True


@with_setup(setup)
def test_is_readable_writable_field():
    lockdown_context.role = None
    lockdown_context.user = None
    lockdown_context.group = None

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

        lockdown_context.role = rest_api

        assert b.is_field_readable(Bicycle.serial) is False
        assert b.is_field_writeable(Bicycle.serial) is False
        assert b.is_field_writeable(Bicycle.modified) is False
        assert b.is_field_writeable(Bicycle.created) is False

        lockdown_context.group = 10
        lockdown_context.user = 10

        assert b.is_field_readable(Bicycle.serial) is False
        assert b.is_field_writeable(Bicycle.serial) is False

        lockdown_context.group = g.id

        assert b.is_field_readable(Bicycle.serial) is True
        assert b.is_field_writeable(Bicycle.serial) is False

        lockdown_context.user = u.id

        assert b.is_field_readable(Bicycle.serial) is True
        assert b.is_field_writeable(Bicycle.serial) is True


@with_setup(setup)
def test_insert():
    lockdown_context.role = None
    lockdown_context.user = None
    lockdown_context.group = None

    rest_api = Role('rest_api')

    rest_api.lockdown(BigWheel) \
        .writeable_by(BigWheel.owner == ContextParam('user'))\
        .validate(BigWheel.owner, BigWheel.owner == ContextParam('user')) \
        .field_writeable_by(BigWheel.serial, BigWheel.owner == ContextParam('user'))

    with test_database(test_db, [User, Group, BigWheel]):
        u1 = User.create(username='test')
        u2 = User.create(username='test')
        g = Group.create(name='test')

        # set the role/user before inserting
        lockdown_context.role = rest_api
        lockdown_context.user = u1.id

        try:
            bwheel = BigWheel()
            bwheel.owner = u2
            bwheel.group = g
            bwheel.serial = '1'
            assert False, 'should have failed'
        except LockdownException:
            pass

        # insert should work fine since object validates
        bwheel = BigWheel()
        bwheel.owner = u1
        bwheel.group = g
        bwheel.serial = '1'
        bwheel.save()

        b = BigWheel.get()
        assert b.modified is not None
        assert b.created is not None
        assert b.serial == '1'
        assert b.owner == u1
        assert b.group == g


@with_setup(setup)
def test_save():
    lockdown_context.role = None
    lockdown_context.user = None
    lockdown_context.group = None

    rest_api = Role('rest_api')
    rest_api.lockdown(Bicycle) \
        .field_readable_by(Bicycle.serial, Bicycle.group == ContextParam('group')) \
        .field_writeable_by(Bicycle.serial, Bicycle.owner == ContextParam('user'))

    with test_database(test_db, [User, Group, Bicycle]):
        u = User.create(username='test')
        g = Group.create(name='test')
        b = Bicycle.create(owner=u, group=g, serial='1')

        lockdown_context.role = rest_api

        try:
            b.serial = '10'
            assert False, 'should have thrown'
        except:
            pass

        assert b.serial == '1'
        b = Bicycle.get()
        assert b.serial is None, 'cant read this field, no group'

        lockdown_context.group = g.id

        b = Bicycle.get()
        assert b.serial == '1', 'now this field can be read, should be 1 still'

        lockdown_context.user = u.id

        b.serial = '10'
        b.save()
        b = Bicycle.get()
        assert b.serial == '10'


@with_setup(setup)
def test_lockdown_user():
    lockdown_context.role = None
    lockdown_context.user = None
    lockdown_context.group = None

    rest_api = Role('rest_api')
    rest_api.lockdown(Bicycle) \
        .field_writeable_by(Bicycle.owner, Bicycle.owner == ContextParam('user'))

    with test_database(test_db, [User, Group, Bicycle]):
        u = User.create(username='test')
        u2 = User.create(username='test2')
        g = Group.create(name='test')
        b = Bicycle.create(owner=u, group=g)

        lockdown_context.role = rest_api

        assert b.is_field_writeable(Bicycle.owner) is False

        lockdown_context.user = 10

        assert b.is_field_writeable(Bicycle.owner) is False
        try:
            b.owner = u2
            assert False, 'should have thrown'
        except:
            pass

        lockdown_context.user = u.id
        assert b.is_field_writeable(Bicycle.owner) is True

@with_setup(setup)
def test_validation():
    rest_api = Role('rest_api')
    rest_api.lockdown(Bicycle)\
        .writeable_by(Bicycle.owner == ContextParam('user'))\
        .validate(Bicycle.owner, Bicycle.owner == ContextParam('user'))\
        .validate(Bicycle.serial, lambda b, f, v: v.startswith('a'))

    with test_database(test_db, [User, Group, Bicycle]):
        b = Bicycle.create()
        u1 = User.create(username='test')
        u2 = User.create(username='test')

        lockdown_context.role = rest_api
        try:
            b.owner = u1
            assert False, 'should have thrown exception'
        except:
            pass

        lockdown_context.user = u1.id
        try:
            b.owner = u2
            assert False, 'should have thrown exception'
        except:
            pass

        lockdown_context.user = u1.id
        b.owner = u1

        b.serial = 'a'
        try:
            b.serial = 'b'
            assert False, 'should have thrown exception'
        except LockdownException:
            pass

@with_setup(setup)
def test_no_one():
    lockdown_context.role = None
    lockdown_context.user = None
    lockdown_context.group = None

    rest_api = Role('rest_api')
    rest_api.lockdown(Bicycle).readable_by(NO_ONE).writeable_by(NO_ONE)

    with test_database(test_db, [User, Group, Bicycle]):
        u = User.create(username='test')
        g = Group.create(name='test')
        b = Bicycle.create(owner=u, group=g)

        lockdown_context.role = rest_api

        assert b.is_readable() is False
        assert b.is_writable() is False

        lockdown_context.group = g.id
        lockdown_context.user = u.id

        assert b.is_readable() is False
        assert b.is_writable() is False


@with_setup(setup)
def test_custom_role_check():
    rest_api = Role('rest_api')
    rest_api.lockdown(Bicycle) \
        .writeable_by((Bicycle.group == ContextParam('group')) &
                      (ContextParam('custom_role') == 'admin'))

    with test_database(test_db, [Group, Bicycle]):
        g = Group.create(name='test')
        b = Bicycle.create(group=g)

        lockdown_context.role = rest_api

        try:
            b.serial = '1'
            assert False, 'should have failed'
        except LockdownException:
            pass

        lockdown_context.group = g.id

        try:
            b.serial = '1'
            assert False, 'should have failed'
        except LockdownException:
            pass

        lockdown_context.custom_role = 'user'
        try:
            b.serial = '1'
            assert False, 'should have failed'
        except LockdownException:
            pass

        lockdown_context.custom_role = 'admin'
        b.serial = '1'


@with_setup(setup)
def test_combined_roles():
    server_api = Role('server_api')
    server_api.lockdown(Bicycle) \
        .writeable_by((Bicycle.group == ContextParam('group')) &
                      (ContextParam('custom_role') == 'admin'))

    rest_api = server_api.extend('rest_api')
    rest_api.lockdown(BaseModel)\
        .field_writeable_by(BaseModel.created, NO_ONE)\
        .field_writeable_by(BaseModel.modified, NO_ONE)

    with test_database(test_db, [Group, Bicycle]):
        g1 = Group.create(name='test1')
        g2 = Group.create(name='test2')
        b = Bicycle.create(group=g1)

        lockdown_context.role = rest_api
        lockdown_context.group = g1.id
        lockdown_context.custom_role = 'admin'

        b.serial = '1'

        # make sure the group rule was inherited from server_api
        lockdown_context.group = g2.id
        try:
            b.serial = '1'
            assert False, 'should have failed'
        except:
            pass

        # set group to the correct group, but shouldn't be able to set created
        # since this is still the rest_api role
        lockdown_context.group = g1.id
        try:
            b.created = datetime.utcnow()
            assert False, 'should have failed'
        except:
            pass

        # server_api can set created
        lockdown_context.role = server_api
        b.created = datetime.utcnow()
