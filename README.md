txdbapi
=======

*For the latest source code, see <http://github.com/fiorix/txdbapi>*


``txdbapi`` is an experimental ORM for [Twisted](http://twistedmatrix.com)
based on [Twistar](http://findingscience.com/twistar/).

Main difference is that ``txdbapi`` support multiple databases, and is
supposed to be a very thin layer on
[t.e.adbapi](http://twistedmatrix.com/documents/current/core/howto/rdbms.html),
on a single file so we can embed in [cyclone](http://cyclone.io).

Currently, it still lack many features, and is a work-in-progress with
absolutely no certainty about its future. We might face obstacles down the
road and the success of this project depends on how much effort it takes to
develop and achieve a usable version.


Notes
-----

Important things to know for developers, and people using it (if they care):

- Only ``sqlite3``, ``MySQLdb`` and ``psycopg2`` are supported
- ``twisted.enterprise.adbapi.ConnectionPool`` may not be used directly
- use ``txdbapi.ConnectionPool`` instead, and it's not really a pool for sqlite
- SQLite does not use ``t.e.adbapi``; it uses an ``InlineSQLite`` instead
- Queries take ``%s`` for their arguments; auto converted to ``?`` for sqlite
- MySQL, Postgres, and SQLite use their custom, optimized ``DictCursor``


### Dependencies ###

Besides twisted:

- For SQLite, the built-in ``sqlite3`` is used
- For MySQL, ``MySQLdb`` is required: ``pip install python-mysql``
- For Postgres, ``psycopg2`` is required: ``pip install psycopg2``


### Unit Tests ###

[Twisted Trial](http://twistedmatrix.com/trac/wiki/TwistedTrial) unit tests
are available.

Run ``trial ./tests`` for all the tests. This requires MySQL and Postgres up
and running. For testing a specific database, run
``trial ./tests/test_sqlite.py``, or ``test_mysql.py``, or
``test_postgres.py``.

[![Build Status](https://secure.travis-ci.org/fiorix/txdbapi.png)](http://travis-ci.org/fiorix/txdbapi)

Usage
-----

For now, all we have is this simple hello world:

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
