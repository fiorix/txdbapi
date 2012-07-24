# coding: utf-8

import sqlite3
import sys

from twisted.enterprise import adbapi
from twisted.internet import defer
from UserDict import UserDict


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


class DatabaseMixin(UserDict):
    db = None

    def __init__(self, *args, **kwargs):
        UserDict.__init__(self, *args, **kwargs)
        self.exists = 1 if "id" in self else 0
        self.changes = set()

    def __setitem__(self, k, v):
        if hasattr(self, "changes"):
            self.changes.add(k)
        UserDict.__setitem__(self, k, v)

    def __getattr__(self, k):
        try:
            return self.__getitem__(k)
        except:
            return None

    def __setattr__(self, k, v):
        if k in ("changes", "data", "db", "exists"):
            self.__dict__[k] = v
        else:
            self.__setitem__(k, v)

    @classmethod
    @defer.inlineCallbacks
    def count(cls, **kwargs):
        if "where" in kwargs:
            where, args = kwargs["where"][0], kwargs["where"][1:]
            rs = yield cls.db.runQuery("select count(*) as count from %s"
                                       "where %s" %
                                       (cls.__name__, where), args)
        else:
            rs = yield cls.db.runQuery("select count(*) as count from %s" %
                                       cls.__name__)

        defer.returnValue(rs[0]["count"])

    @classmethod
    @defer.inlineCallbacks
    def find(cls, **kwargs):
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
            where, args = kwargs["where"][0], kwargs["where"][1:]
            rs = yield cls.db.runQuery("select %s from %s where %s %s" %
                                       (star, cls.__name__, where, extra),
                                       args)
        else:
            rs = yield cls.db.runQuery("select %s from %s %s" %
                                       (star, cls.__name__, extra))

        if isinstance(cls.db, InlineSQLite):
            result = map(lambda row: cls(dict(row)), rs)
        else:
            result = map(cls, rs)
        defer.returnValue(result[0] if kwargs.get("limit") == 1 else result)

    @classmethod
    def all(cls):
        return cls.find()

    @defer.inlineCallbacks
    def delete(self):
        assert self.get("id"), "This object has not been saved yet."
        yield self.db.runOperation("delete from %s where id=%s" %
                                   (self.__class__.__name__, self["id"]))
        self.changes.clear()
        self.exists = 0
        defer.returnValue(self.pop("id"))

    @defer.inlineCallbacks
    def save(self, force_update=False):
        if force_update:
            self.exists = 1

        if self.exists:
            if not self.changes:
                raise ValueError("No changes to commit")

            v = []
            q = ["update %s set" % self.__class__.__name__]
            for k in self.changes:
                q.append("%s=%s" % (k, "%s"))
                v.append(self[k])

            self.changes.clear()
            q.append("where id=%s" % self["id"])
            yield self.db.runOperation(" ".join(q), v)
            defer.returnValue(self["id"])

        else:
            keys = self.keys()
            q = "insert into %s (%s) values " % (self.__class__.__name__,
                                                 ",".join(keys)) + "(%s)"

            vs = []
            vb = []
            for k in keys:
                vs.append("%s")
                vb.append(self[k])

            if isinstance(self.db, InlineSQLite):
                vs = ["?"] * len(vs)
            r = yield self.db.runInteraction(self._insert_transaction,
                                             q % ",".join(vs), vb)

            self["id"] = r[0]["id"]
            self.exists = 1
            defer.returnValue(self["id"])

    def _insert_transaction(self, trans, *args, **kwargs):
        trans.execute(*args, **kwargs)
        if isinstance(self.db, InlineSQLite):
            trans.execute("select last_insert_rowid() as id")
        elif self.db.dbapiName == "MySQLdb":
            trans.execute("select last_insert_id() as id")
        elif self.db.dbapiName == "psycopg2":
            trans.execute("select currval('%s_id_seq') as id" %
                          self.__class__.__name__)
        return trans.fetchall()

    def __str__(self):
        return repr(self)
