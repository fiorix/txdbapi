#!/usr/bin/env python
# coding: utf-8

import txdbapi

from twisted.internet import defer
from twisted.internet import reactor


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


@defer.inlineCallbacks
def main():
    yield BaseModel.setup()

    # create foo
    foo = asd.new(name="foo", age=10)
    yield foo.save()
    print "foo=", foo

    # create bar
    bar = asd.new()
    bar.name = "bar"
    bar.age = 11
    yield bar.save()
    print "bar=", bar

    # count
    nobjs = yield asd.count()
    print "nobjs:", nobjs

    # query and update
    objs = yield asd.find(where=("name in (%s, %s)", "foo", "bar"))
    for obj in objs:
        obj.age += 10
        yield obj.save()
        print obj

    reactor.stop()


if __name__ == "__main__":
    reactor.callWhenRunning(main)
    reactor.run()
