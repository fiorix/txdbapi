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


Usage
-----

For now, all we have is this simple hello world:

    import txdbapi

    from twisted.internet import defer
    from twisted.internet import reactor


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


    @defer.inlineCallbacks
    def main():
        yield Model.setup()

        obj = asd(name="foo", age=10)
        yield obj.save()

        obj = asd(name="bar", age=11)
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


And it works. :)
