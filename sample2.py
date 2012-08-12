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
                "create table users (id integer primary key autoincrement, "
                "name text, phone integer)")

        yield BaseModel.db.runOperation(
                "create table phones (id integer primary key autoincrement, "
                "model text, features text)")

        yield BaseModel.db.runOperationMany(
                "insert into phones (model, features) values (%s, %s)",
                (["iPhone", "A"], ["Android", "B"], ["Blackberry", "C"]))

        yield BaseModel.db.runOperationMany(
                "insert into users (name, phone) values (%s, %s)",
                (["tuna1", 1], ["tuna2", 2], ["tuna3", 3],
                 ["aldrA", 1], ["aldrB", 2],
                 ["cassX", 3]))


class phones(BaseModel):
    pass


class users(BaseModel):
    pass


@defer.inlineCallbacks
def main():
    yield BaseModel.setup()

    iphone = yield phones.find_first(where=("model=%s", "iPhone"))
    print "iphone=", repr(iphone)

    newuser = yield users.insert(name="foobar", phone=iphone)
    print "new user=", repr(newuser)

    usercount = yield users.count()
    print "%d users found" % usercount

    iphone_users = yield users.find(where=("phone=%s", iphone))
    for user in iphone_users:
        print user

    reactor.stop()


if __name__ == "__main__":
    reactor.callWhenRunning(main)
    reactor.run()
