# coding: utf-8

import txdbapi

from twisted.internet import base
from twisted.internet import defer
from twisted.trial import unittest

base.DelayedCall.debug = False


class Model(txdbapi.DatabaseMixin):
    db = txdbapi.ConnectionPool("sqlite3", ":memory:")

    @classmethod
    @defer.inlineCallbacks
    def setup(cls):
        yield Model.db.runOperation(
            "create table asd "
            "(id integer primary key autoincrement, age int, name text)")


class asd(Model):
    pass


class TestSQLite(unittest.TestCase):
    @defer.inlineCallbacks
    def test_basic(self):
        yield Model.setup()

        obj = asd(name="foo", age=10)
        yield obj.save()

        obj = asd(name="bar", age=11)
        yield obj.save()

        rs = yield asd.all()

        obj1 = rs[0]
        self.assertEqual(obj1.id, 1)
        self.assertEqual(obj1.age, 10)
        self.assertEqual(obj1.name, "foo")

        obj2 = rs[1]
        self.assertEqual(obj2.id, 2)
        self.assertEqual(obj2.age, 11)
        self.assertEqual(obj2.name, "bar")

    @defer.inlineCallbacks
    def test_count(self):
        nobjs = yield asd.count()
        self.assertEqual(nobjs, 2)

    @defer.inlineCallbacks
    def test_query1(self):
        obj = yield asd.find(where=("name=%s", "foo"), limit=1)
        self.assertEqual(obj.id, 1)
        self.assertEqual(obj.age, 10)
        self.assertEqual(obj.name, "foo")

    @defer.inlineCallbacks
    def test_query2(self):
        obj = yield asd.find(where=("name=%s", "bar"), limit=1)
        self.assertEqual(obj.id, 2)
        self.assertEqual(obj.age, 11)
        self.assertEqual(obj.name, "bar")
