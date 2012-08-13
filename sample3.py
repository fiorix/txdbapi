#!/usr/bin/env python
# coding: utf-8

import json
import txdbapi

from twisted.internet import defer
from twisted.internet import reactor


class BaseModel(txdbapi.DatabaseModel):
    db = txdbapi.ConnectionPool("sqlite3", ":memory:")

    @classmethod
    @defer.inlineCallbacks
    def setup(cls):
        yield BaseModel.db.runOperation(
            "create table asd1 "
            "(id integer primary key autoincrement, age int, name text)")

        yield BaseModel.db.runOperation(
            "create table asd2 "
            "(id integer primary key autoincrement, age int, name text)")


class asd1(BaseModel):
    deny = ["x", "y"]


class asd2(BaseModel):
    allow = ["name", "age"]
    codecs = {"name": (json.dumps, json.loads)}


@defer.inlineCallbacks
def main():
    yield BaseModel.setup()

    # create foo
    foo = asd1.new(name="foo", age=10, x=1, y=2)
    yield foo.save()
    print "foo=", foo

    foo = yield asd1.select(where=("id=%s", foo.id))
    print "foo from db:", foo  # without x and y

    # create bar
    bar = asd2.new()
    bar.name = {"first": "bar", "last": "smith"}
    bar.age = 11
    bar.x = 1
    bar.y = 2
    yield bar.save()
    print "bar=", bar, "bar.name=", repr(bar.name)

    bar = yield asd2.select(where=("id=%s", bar.id))
    print "bar from db:", bar  # without x and y

    reactor.stop()


if __name__ == "__main__":
    reactor.callWhenRunning(main)
    reactor.run()
