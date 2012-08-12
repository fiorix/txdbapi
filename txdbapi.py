# coding: utf-8
# http://en.wikipedia.org/wiki/Active_record_pattern
# http://en.wikipedia.org/wiki/Create,_read,_update_and_delete

import sqlite3
import sys

from twisted.enterprise import adbapi
from twisted.internet import defer


class InlineSQLite:
    def __init__(self, dbname, autocommit=True, cursorclass=None):
        self.autocommit = autocommit
        self.conn = sqlite3.connect(dbname)
        if cursorclass:
            self.conn.row_factory = cursorclass

        self.curs = self.conn.cursor()

    def runQuery(self, query, *args, **kwargs):
        self.curs.execute(query.replace("%s", "?"), *args, **kwargs)
        return self.curs.fetchall()

    def runOperation(self, command, *args, **kwargs):
        self.curs.execute(command.replace("%s", "?"), *args, **kwargs)
        if self.autocommit is True:
            self.conn.commit()

    def runOperationMany(self, command, *args, **kwargs):
        self.curs.executemany(command.replace("%s", "?"), *args, **kwargs)
        if self.autocommit is True:
            self.conn.commit()

    def runInteraction(self, interaction, *args, **kwargs):
        return interaction(self.curs, *args, **kwargs)

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()


def ConnectionPool(dbapiName, *args, **kwargs):
    if dbapiName == "sqlite3":
        if sys.version_info < (2, 6):
            # hax for py2.5
            def __row(cursor, row):
                d = {}
                for idx, col in enumerate(cursor.description):
                    d[col[0]] = row[idx]
                return d

            kwargs["cursorclass"] = __row
        else:
            kwargs["cursorclass"] = sqlite3.Row

        return InlineSQLite(*args, **kwargs)

    elif dbapiName == "MySQLdb":
        import MySQLdb.cursors
        kwargs["cursorclass"] = MySQLdb.cursors.DictCursor
        return adbapi.ConnectionPool(dbapiName, *args, **kwargs)

    elif dbapiName == "psycopg2":
        import psycopg2
        import psycopg2.extras
        psycopg2.connect = psycopg2.extras.RealDictConnection
        return adbapi.ConnectionPool(dbapiName, *args, **kwargs)

    else:
        raise ValueError("Database %s is not yet supported." % dbapiName)


class DatabaseObject(object):
    def __init__(self, model, row):
        self._model = model
        self._changes = set()
        self._data = dict(row)

    def __setattr__(self, k, v):
        if k[0] == "_":
            object.__setattr__(self, k, v)
        else:
            if k in self._data:
                self._changes.add(k)

            self._data[k] = v

    def __getattr__(self, k):
        if [0] == "_":
            object.__getattr__(self, k)
        else:
            return self._data[k]

    def __setitem__(self, k, v):
        self.__setattr__(k, v)

    def __getitem__(self, k):
        return self.__getattr__(k)

    def get(self, k, default=None):
        return self._data.get(k, default)

    @defer.inlineCallbacks
    def save(self, force=False):
        if "id" in self._data:
            if self._changes and not force:
                kv = dict(map(lambda k: (k, self._data[k]), self._changes))
                kv["where"] = ("id=%s", self._data["id"])
                yield self._model.update(**kv)
            elif force:
                k, v = self._data.items()
                yield self._model.update(set=(k, v),
                                         where=("id=%s", self._data["id"]))

            self._changes.clear()
            defer.returnValue(self)
        else:
            rs = yield self._model.insert(**self._data)
            self["id"] = rs["id"]
            defer.returnValue(self)

    def __repr__(self):
        return repr(self._data)


class DatabaseCRUD(object):
    db = None
    allow = []
    deny = []

    @classmethod
    def __table__(cls):
        return getattr(cls, "table_name", cls.__name__)

    @classmethod
    @defer.inlineCallbacks
    def insert(cls, **kwargs):
        if cls.allow:
            cls.deny += [k for k in kwargs if k not in cls.allow]

        if cls.deny:
            map(lambda k: kwargs.pop(k, None), cls.deny)

        keys = kwargs.keys()
        q = "insert into %s (%s) values " % (cls.__table__(),
                                             ",".join(keys)) + "(%s)"

        vs = []
        vd = []
        for v in kwargs.itervalues():
            vs.append("%s")
            vd.append(v["id"] if isinstance(v, DatabaseObject) else v)

        if isinstance(cls.db, InlineSQLite):
            vs = ["?"] * len(vs)

        q = q % ",".join(vs)

        if "id" in kwargs:
            yield cls.db.runOperation(q, vd)
        else:
            def _insert_transaction(trans, *args, **kwargs):
                trans.execute(*args, **kwargs)
                if isinstance(cls.db, InlineSQLite):
                    trans.execute("select last_insert_rowid() as id")
                elif cls.db.dbapiName == "MySQLdb":
                    trans.execute("select last_insert_id() as id")
                elif cls.db.dbapiName == "psycopg2":
                    trans.execute("select currval('%s_id_seq') as id" %
                                  cls.__table__())
                return trans.fetchall()

            r = yield cls.db.runInteraction(_insert_transaction, q, vd)
            kwargs["id"] = r[0]["id"]

        defer.returnValue(DatabaseObject(cls, kwargs))

    @classmethod
    def update(cls, **kwargs):
        where = kwargs.pop("where", None)

        keys = kwargs.keys()
        vals = [kwargs[k] for k in keys]
        keys = ",".join(["%s=%s" % (k, "%s") for k in keys])

        if where:
            where, args = where[0], list(where[1:])
            for arg in args:
                if isinstance(arg, DatabaseObject):
                    vals.append(arg["id"])
                else:
                    vals.append(arg)

            return cls.db.runOperation("update %s set %s where %s" %
                                       (cls.__table__(), keys, where), vals)
        else:
            return cls.db.runOperation("update %s set %s" %
                                       (cls.__table__(), keys), vals)

    @classmethod
    @defer.inlineCallbacks
    def select(cls, **kwargs):
        extra = []
        star = "id,*" if isinstance(cls.db, InlineSQLite) else "*"

        if "groupby" in kwargs:
            extra.append("group by %s" % kwargs["groupby"])

        if "orderby" in kwargs:
            extra.append("order by %s" % kwargs["orderby"])

        if "asc" in kwargs and kwargs["asc"] is True:
            extra.append("asc")

        if "desc" in kwargs and kwargs["desc"] is True:
            extra.append("desc")

        if "limit" in kwargs:
            extra.append("limit %s" % kwargs["limit"])

        if "offset" in kwargs:
            extra.append("offset %s" % kwargs["offset"])

        extra = " ".join(extra)

        if "where" in kwargs:
            where, args = kwargs["where"][0], list(kwargs["where"][1:])
            for n, arg in enumerate(args):
                if isinstance(arg, DatabaseObject):
                    args[n] = arg["id"]

            rs = yield cls.db.runQuery("select %s from %s where %s %s" %
                                       (star, cls.__table__(), where, extra),
                                       args)
        else:
            rs = yield cls.db.runQuery("select %s from %s %s" %
                                       (star, cls.__table__(), extra))

        result = map(lambda d: DatabaseObject(cls, d), rs)
        defer.returnValue(result)

    @classmethod
    def delete(cls, **kwargs):
        if "where" in kwargs:
            where, args = kwargs["where"][0], kwargs["where"][1:]
            cls.db.runOperation("delete from %s where %s" %
                                (cls.__table__(), where), args)
        else:
            cls.db.runOperation("delete from %s" % cls.__table__())

    def __str__(self):
        return str(self.data)


class DatabaseModel(DatabaseCRUD):
    @classmethod
    @defer.inlineCallbacks
    def count(cls, **kwargs):
        if "where" in kwargs:
            where, args = kwargs["where"][0], kwargs["where"][1:]
            rs = yield cls.db.runQuery("select count(*) as count from %s"
                                       "where %s" %
                                       (cls.__table__(), where), args)
        else:
            rs = yield cls.db.runQuery("select count(*) as count from %s" %
                                       cls.__table__())

        defer.returnValue(rs[0]["count"])

    @classmethod
    def all(cls):
        return cls.select()

    @classmethod
    def find(cls, **kwargs):
        return cls.select(**kwargs)

    @classmethod
    @defer.inlineCallbacks
    def find_first(cls, **kwargs):
        kwargs["limit"] = 1
        rs = yield cls.select(**kwargs)
        defer.returnValue(rs[0] if rs else None)

    @classmethod
    def new(cls, **kwargs):
        return DatabaseObject(cls, kwargs)
