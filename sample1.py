#!/usr/bin/env python
# coding: utf-8

import txdbapi

from twisted.internet import defer
from twisted.internet import reactor


class Model(txdbapi.DatabaseModel):
    db = txdbapi.ConnectionPool("sqlite3", ":memory:")

    @classmethod
    @defer.inlineCallbacks
    def setup(cls):
        yield Model.db.runOperation(
            "create table asd "
            "(id integer primary key autoincrement, age int, name text)")


class asd(Model):
    pass


@defer.inlineCallbacks
def main():
    yield Model.setup()

    obj = asd.new(name="foo", age=10)
    yield obj.save()

    obj = asd.new(name="bar", age=11)
    yield obj.save()

    nobjs = yield asd.count()
    print "objects:", nobjs

    for name in ("foo", "bar"):
        obj = yield asd.find(where=("name=%s", name), limit=1)
        print obj

    reactor.stop()


if __name__ == "__main__":
    reactor.callWhenRunning(main)
    reactor.run()
