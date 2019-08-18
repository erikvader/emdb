
import sqlite3 as S
from contextlib import contextmanager, closing
import re
from collections import deque
from itertools import chain

def _glob_to_regex(glob):
   reg = re.escape(glob)
   reg = re.sub(r"\\\*", r".*?", reg)
   return re.compile(reg)

class Database:

   class DBError(Exception):
      pass

   def __init__(self, dbfile):
      self.dbfile = dbfile
      self.conn = S.connect(dbfile)
      self.conn.execute("PRAGMA foreign_keys = ON").close()

   def close(self):
      self.conn.close()

   # random ###################################################################
   @staticmethod
   def _tpid(pid=None, tid=None):
      assert bool(pid) != bool(tid)
      if pid:
         return pid, "pid", "Starring"
      else:
         return tid, "tid", "Tagging"

   # context managers #########################################################
   def _cursor(self):
      return closing(self.conn.cursor())

   @contextmanager
   def _transaction(self):
      with self.conn:
         with self._cursor() as c:
            yield c

   # basic sql operations #####################################################
   def _exists(self, cursor, table, cond=""):
      res = self._get_all_from(cursor, table, cond)
      return res != []

   def _insert_into(self, cursor, table, values):
      columns = ""
      vals = []
      for k,v in values.items():
         columns += k + ","
         vals.append(v)
      columns = columns[:-1]
      questions = "?," * len(vals)
      questions = questions[:-1]

      cursor.execute(
         "insert into {}({}) values ({})".format(
            table, columns, questions
         ),
         tuple(vals)
      )
      return cursor.lastrowid

   def _remove_all_from(self, cursor, table, cond=""):
      cursor.execute(
         "delete from {}{}".format(
            table,
            " where {}".format(cond) if cond else ""
         )
      )
      return cursor.rowcount > 0

   def _get_all_from(self, cursor, table, cond=""):
      res = cursor.execute(
         "select * from {}{}".format(
            table,
            " where {}".format(cond) if cond else ""
         )
      )
      return [{n[0]: v for n,v in zip(cursor.description, r)} for r in res]

   def _modify(self, cursor, table, key, values):
      s = ""
      vals = []
      for k,v in values.items():
         if k != key:
            s += str(k) + "=?,"
            vals.append(v)
      s = s[:-1]
      cursor.execute(
         "update {} set {} where {} = ?".format(
            table,
            s,
            key
         ),
         tuple(vals + [values[key]])
      )

   # links ####################################################################
   def _unlink(self, cursor, mid, pid=None, tid=None):
      tpid, tpid_name, table = Database._tpid(pid, tid)
      return self._remove_all_from(cursor, table, "mid = {} and {} = {}".format(mid, tpid_name, tpid))

   def _link(self, cursor, mid, pid=None, tid=None):
      tpid, tpid_name, table = Database._tpid(pid, tid)
      return self._insert_into(cursor,table, {"mid": mid, tpid_name: tpid})

   def _link_set(self, cursor, mid, ids, pid=None, tid=None):
      _, tpid_name, table = Database._tpid(pid, tid)
      old = self._get_all_from(cursor, table, "mid = {}".format(mid))
      old = {o[tpid_name] for o in old}
      new = set(ids)
      toremove = old - new
      toadd = new - old

      a = {"pid": None, "tid": None}
      for tr in toremove:
         self._unlink(cursor, mid, **{**a, tpid_name: tr})

      for ta in toadd:
         self._link(cursor, mid, **{**a, tpid_name: ta})

   # pornstar related #########################################################
   def _get_stars_for(self, cursor, mid):
      res = self._get_all_from(cursor, "Starring", "mid = {}".format(mid))
      return [r["pid"] for r in res]

   def _get_star_info(self, cursor, pid):
      res = self._get_all_from(cursor, "Pornstar", "id = {}".format(pid))
      if res:
         return res[0]
      raise self.DBError("pid {} doesn't exist".format(pid))

   def _add_star(self, cursor, name):
      return self._insert_into(cursor, "Pornstar", {"name": name})

   # tag related ##############################################################
   def _add_tag(self, cursor, name, subsetof):
      toadd = {"name": name}
      if subsetof:
         toadd["subsetof"] = subsetof
      return self._insert_into(cursor, "Tag", toadd)

   def _get_tags_for(self, cursor, mid):
      res = self._get_all_from(cursor, "Tagging", "mid = {}".format(mid))
      return [r["tid"] for r in res]

   def _get_derived_tags_for(self, cursor, mid):
      queue = self._get_tags_for(cursor, mid)
      visited = set()
      while queue:
         eid = queue.pop(0)
         visited.add(eid)
         subs = self._get_all_from(cursor, "Tag", "subsetof = {}".format(eid))
         subs = (s["id"] for s in subs)
         for s in subs:
            if s not in visited:
               queue.append(s)

      return list(visited)

   def _get_superset_tags_for(self, cursor, mid):
      tags = self._get_tags_for(cursor, mid)
      all_supers = self._get_tags_supersets(cursor, tags)
      return list(chain(tags, all_supers))

   def _get_tag_info(self, cursor, tid):
      res = self._get_all_from(cursor, "Tag", "id = {}".format(tid))
      if res:
         return res[0]
      raise self.DBError("tid {} doesn't exist".format(tid))

   def _get_tags_supersets(self, c, tags):
      def find_supersets(tid):
         while True:
            tid = self._get_tag_info(c, tid)["subsetof"]
            if tid:
               yield tid
            else:
               break

      all_supers = chain.from_iterable(find_supersets(t) for t in tags)
      return set(all_supers)

   def _remove_redundant_tags(self, c, tags):
      all_supers = self._get_tags_supersets(c, tags)
      return [t for t in tags if not t in all_supers]

   # public interface #########################################################
   def add_movie(self, filename, name, starred, stars, tags):
      #ppylint: disable=no-member
      with self._transaction() as c:
         mid = self._insert_into(
            c,
            "Movie",
            {"path": filename, "name": name, "starred": int(starred)}
         )
         if stars:
            self._link_set(c, mid, stars, pid=True)
         if tags:
            t = self._remove_redundant_tags(c, tags)
            self._link_set(c, mid, t, tid=True)

         return self.get_movies(mid)[0]

   def remove_movie(self, mid):
      with self._transaction() as c:
         self._remove_all_from(c, "Movie", "id = {}".format(mid))

   def set_tags_for(self, mid, tags):
      with self._transaction() as c:
         t = self._remove_redundant_tags(c, tags)
         self._link_set(c, mid, t, tid=True)

   def set_stars_for(self, mid, stars):
      with self._transaction() as c:
         self._link_set(c, mid, stars, pid=True)

   def set_starred_for(self, mid, starred):
      with self._transaction() as c:
         self._modify(c, "Movie", "id", {"id": mid, "starred": int(starred)})

   def set_name_for(self, mid, name):
      with self._transaction() as c:
         self._modify(c, "Movie", "id", {"id": mid, "name": name})

   def add_star(self, name):
      with self._transaction() as c:
         self._add_star(c, name)

   def add_tag(self, name, subsetof=None):
      with self._transaction() as c:
         self._add_tag(c, name, subsetof)

   def get_movies(self, mid=None):
      with self._cursor() as c:
         movies = self._get_all_from(c, "Movie", "id = {}".format(mid) if mid else "")
         return [Movie(self, m) for m in movies]

   def get_stars_for(self, mid):
      with self._cursor() as c:
         stars = self._get_stars_for(c, mid)
         return [Star(self._get_star_info(c, pid)) for pid in stars]

   def get_tags_for(self, mid):
      with self._cursor() as c:
         tags = self._get_tags_for(c, mid)
         return [Tag(self._get_tag_info(c, tid)) for tid in tags]

   def get_superset_tags_for(self, mid):
      with self._cursor() as c:
         tags = self._get_superset_tags_for(c, mid)
         return [Tag(self._get_tag_info(c, tid)) for tid in tags]

   def get_tags(self):
      with self._cursor() as c:
         return [Tag(x) for x in self._get_all_from(c, "Tag")]

   def get_stars(self):
      with self._cursor() as c:
         return [Star(x) for x in self._get_all_from(c, "Pornstar")]

#pylint: disable=protected-access
class Movie:
   def __init__(self, db, movie_dict):
      self.db = db
      self.mdict = movie_dict
      self.stars = None
      self.tags = None
      self.derived_tags = None
      self.superset_tags = None

   def get_id(self):
      return self.mdict["id"]

   def get_added_date(self):
      from datetime import datetime
      return datetime.fromtimestamp(self.mdict["added_date"])

   def get_path(self):
      return self.mdict["path"]

   def get_name(self):
      return self.mdict["name"]

   def get_disp(self):
      return self.get_name() if self.get_name() else self.get_path()

   def is_starred(self):
      return bool(self.mdict["starred"])

   def get_stars(self):
      if not self.stars:
         self.stars = self.db.get_stars_for(self.get_id())
      return self.stars

   def get_tags(self):
      if not self.tags:
         self.tags = self.db.get_tags_for(self.get_id())
      return self.tags

   def get_derived_tags(self):
      if not self.derived_tags:
         self.derived_tags = self.db.get_tags_for(self.get_id())
      return self.derived_tags

   def get_superset_tags(self):
      if not self.superset_tags:
         self.superset_tags = self.db.get_superset_tags_for(self.get_id())
      return self.superset_tags

   def set_tags(self, tags):
      self.tags = None
      self.db.set_tags_for(self.get_id(), tags)

   def set_stars(self, stars):
      self.stars = None
      self.db.set_stars_for(self.get_id(), stars)

   def set_starred(self, starred):
      self.mdict["starred"] = int(starred)
      self.db.set_starred_for(self.get_id(), starred)

   def set_name(self, name):
      self.mdict["name"] = name
      self.db.set_name_for(self.get_id(), name)

   def remove_self(self):
      self.db.remove_movie(self.get_id())

   def _has_tagstar(self, glob, cands):
      r = _glob_to_regex(glob)
      if cands:
         cands = (t.get_name().lower() for t in cands)
      else:
         cands = [""]
      return any(r.fullmatch(tn) for tn in cands)

   def has_tag(self, glob):
      return self._has_tagstar(glob, self.get_superset_tags())

   def has_star(self, glob):
      return self._has_tagstar(glob, self.get_stars())

   def __str__(self):
      return self.get_disp()

   def __repr__(self):
      return "movie: {}, stars: {}, tags: {}".format(self.mdict, self.get_stars(), self.get_tags())

   def __eq__(self, other):
      if isinstance(other, type(self)):
         return self.get_id() == other.get_id()
      return False

class _TagStar():
   def __init__(self, tagstar_dict):
      self.name = tagstar_dict["name"]
      self.id = tagstar_dict["id"]

   def get_id(self):
      return self.id

   def get_name(self):
      return self.name

   def __str__(self):
      return self.get_name()

   def __eq__(self, other):
      if isinstance(other, type(self)):
         return self.get_id() == other.get_id()
      return False

class Tag(_TagStar):
   pass

class Star(_TagStar):
   pass

class Search():
   class ParseError(Exception):
      pass

   def __init__(self, string):
      self.ast = None
      self.keywords = {"(", ")", "t", 0, "or", "and", "not", "p", "''", "s"}
      self.tokens = deque(Search._tokenize(string))

      acc = []
      self._search_string(acc)
      self._lstrip(acc)
      self.ast = compile("".join(acc), "<string>", "eval")

   @staticmethod
   def _tokenize(string):
      seps = {" ", "(", ")"}
      word = []
      for c in string:
         if c in seps:
            if word:
               yield "".join(word)
               word.clear()
            yield c
         else:
            word.append(c)
      if word:
         yield "".join(word)
      yield 0

   def _spaces(self, acc, throw=False):
      while True:
         n = self.tokens.popleft()
         if n == " ":
            if not throw:
               acc.append(n)
         else:
            self.tokens.appendleft(n)
            break

   def _rstrip(self, acc):
      while acc and acc[-1] == " ":
         acc.pop()

   def _lstrip(self, acc):
      while acc and acc[0] == " ":
         acc.pop(0)

   def _search_string(self, acc):
      self._expression(acc)
      n = self.tokens.popleft()
      if n != 0:
         raise self.ParseError("not everything was read")

   def _expression(self, acc):
      while True:
         self._spaces(acc, throw=True)
         self._negetable(acc)
         n = self.tokens.popleft()
         if n == "or" or n == "and":
            acc.append(" ")
            acc.append(n)
            acc.append(" ")
         else:
            self.tokens.appendleft(n)
            break

   def _negetable(self, acc):
      n = self.tokens.popleft()
      if n == "not":
         acc.append(" ")
         acc.append("not")
         acc.append(" ")
         self._spaces(acc, throw=True)
      else:
         self.tokens.appendleft(n)
      self._booly(acc)

   def _booly(self, acc):
      n = self.tokens.popleft()
      if n == "(":
         acc.append(n)
         self._expression(acc)
         n = self.tokens.popleft()
         if n != ")":
            raise self.ParseError("unbalanced parens")
         acc.append(n)
         self._spaces(acc, throw=True)
      elif n == "t":
         acc.append("m.has_tag(\"")
         self._spaces(acc, throw=True)
         self._words(acc)
         acc.append("\")")
      elif n == "p":
         acc.append("m.has_star(\"")
         self._spaces(acc, throw=True)
         self._words(acc)
         acc.append("\")")
      elif n == "s":
         acc.append("m.is_starred()")
         self._spaces(acc, throw=True)
      else:
         raise self.ParseError("wanted a booly identifier")

   def _words(self, acc):
      foundone = False
      while True:
         n = self.tokens.popleft()
         if n in self.keywords and n != "''":
            self.tokens.appendleft(n)
            if not foundone:
               raise self.ParseError("no words")
            self._rstrip(acc)
            break
         else:
            foundone = True
            acc.append("" if n == "''" else n)
            self._spaces(acc)

   def match(self, movie):
      #pylint: disable=eval-used
      return eval(self.ast, {"m": movie})
