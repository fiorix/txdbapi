# coding: utf-8

import txdbapi

from twisted.internet import base
from twisted.internet import defer
from twisted.trial import unittest

base.DelayedCall.debug = False


class BaseModel(txdbapi.DatabaseModel):
    db = txdbapi.ConnectionPool("sqlite3", ":memory:")

    @classmethod
    @defer.inlineCallbacks
    def setup(cls):
        yield BaseModel.db.runOperation(
            "create table asd "
            "(id integer primary key autoincrement, age int, name text)")


class asd(BaseModel):
    pass


class Test_SQLite(unittest.TestCase):
    @defer.inlineCallbacks
    def test_01_setup(self):
        yield BaseModel.setup()

    @defer.inlineCallbacks
    def test_02_crud_insert(self):
        foo = yield asd.insert(name="foo", age=10)
        self.assertEqual(foo.id, 1)

        bar = yield asd.insert(name="bar", age=10)
        self.assertEqual(bar.id, 2)

    @defer.inlineCallbacks
    def test_03_crud_update(self):
        yield asd.update(age=20, where=("name=%s", "foo"))
        objs = yield asd.select(where=("name=%s", "foo"))
        foo = objs[0]
        self.assertEqual(foo.id, 1)
        self.assertEqual(foo.age, 20)

    def test_04_crud_select(self):
        foo = yield asd.select(where=("name=%s and age=%s", "foo", 20))
        self.assertEqual(foo.id, 1)

    def test_05_crud_delete(self):
        yield asd.delete(where=("name=%s", "bar"))
        objs = yield asd.select()
        self.assertEqual(len(objs), 1)

    def test_06_model_new(self):
        bar = yield asd.new(name="bar", age=10)
        yield bar.save()
        self.assertEqual(bar.id, 3)

    def test_07_model_all(self):
        objs = yield asd.all()
        self.assertEqual(len(objs), 2)

    @defer.inlineCallbacks
    def test_08_model_count(self):
        nobjs = yield asd.count()
        self.assertEqual(nobjs, 2)

    def test_09_model_find(self):
        objs = yield asd.find(where=("name=%s", "foo"))
        self.assertEqual(objs[0].id, 1)

    def test_10_model_find_first(self):
        bar = yield asd.find_first(where=("name=%s", "bar"))
        self.assertEqual(bar.id, 3)
