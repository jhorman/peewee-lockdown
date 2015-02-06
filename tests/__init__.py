from __future__ import absolute_import
import logging
import datetime
from peewee import SqliteDatabase
import peewee
from lockdown.model import SecureModel

logging.getLogger('peewee').setLevel(level=logging.ERROR)

test_db = SqliteDatabase(':memory:')


class BaseModel(SecureModel):
    created = peewee.DateTimeField(default=datetime.datetime.utcnow)
    modified = peewee.DateTimeField(default=datetime.datetime.utcnow)


class User(BaseModel):
    username = peewee.CharField(null=False)


class Group(BaseModel):
    name = peewee.CharField(null=False)


class Bicycle(BaseModel):
    owner = peewee.ForeignKeyField(User, related_name='bikes', null=True)
    group = peewee.ForeignKeyField(Group, related_name='bikes', null=True)
    serial = peewee.CharField(null=True)


class BigWheel(BaseModel):
    owner = peewee.ForeignKeyField(User, related_name='bigwheels', null=False)
    group = peewee.ForeignKeyField(Group, related_name='bigwheels', null=False)
    serial = peewee.CharField(null=True)
