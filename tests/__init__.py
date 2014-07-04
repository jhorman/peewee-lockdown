from __future__ import absolute_import
from peewee import SqliteDatabase
import peewee
from lockdown.model import SecureModel


test_db = SqliteDatabase(':memory:')


class User(SecureModel):
    username = peewee.CharField(null=False)


class Group(SecureModel):
    name = peewee.CharField(null=False)


class Bicycle(SecureModel):
    owner = peewee.ForeignKeyField(User, related_name='bikes')
    group = peewee.ForeignKeyField(Group, related_name='bikes')
    serial = peewee.CharField(null=True)
