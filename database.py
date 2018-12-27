
import sqlite3 as S
from contextlib import contextmanager, closing

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

   def _get_tags_for(self, cursor, mid, derived):
      res = self._get_all_from(cursor, "Tagging", "mid = {}".format(mid))
      if not derived:
         return [r["tid"] for r in res]

      visited = set()
      queue = [r["tid"] for r in res]
      while queue:
         eid = queue.pop(0)
         visited.add(eid)
         subs = self._get_all_from(cursor, "Tag", "subsetof = {}".format(eid))
         subs = (s["id"] for s in subs)
         for s in subs:
            if s not in visited:
               queue.append(s)

      return list(visited)

   def _get_tag_info(self, cursor, tid):
      res = self._get_all_from(cursor, "Tag", "id = {}".format(tid))
      if res:
         return res[0]
      raise self.DBError("tid {} doesn't exist".format(tid))

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
            self._link_set(c, mid, tags, tid=True)

         return self.get_movies(mid)[0]

   def set_tags_for(self, mid, tags):
      with self._transaction() as c:
         self._link_set(c, mid, tags, tid=True)

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

   # def modify_movie(self, movie):
   #    with self._transaction() as c:
   #       m = movie.copy()
   #       tags = m.pop("tagging")
   #       stars = m.pop("starring")
   #       m["starred"] = int(m["starred"])
   #       self._modify(c, "Movie", "id", m)
   #       self._link_set(c, m["id"], [s["id"] for s in stars], pid=True)
   #       self._link_set(c, m["id"], [t["id"] for t in tags], tid=True)

   def get_stars_for(self, mid):
      with self._cursor() as c:
         stars = self._get_stars_for(c, mid)
         return [Star(self._get_star_info(c, pid)) for pid in stars]

   def get_tags_for(self, mid, derived=True):
      with self._cursor() as c:
         tags = self._get_tags_for(c, mid, derived)
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

   def get_id(self):
      return self.mdict["id"]

   def get_added_date(self):
      # TODO: convert to a python date or something
      return self.mdict["added_date"]

   def get_path(self):
      return self.mdict["path"]

   def get_name(self):
      return self.mdict["name"]

   def is_starred(self):
      return bool(self.mdict["starred"])

   def get_stars(self):
      if not self.stars:
         self.stars = self.db.get_stars_for(self.get_id())
      return self.stars

   def get_tags(self):
      if not self.tags:
         self.tags = self.db.get_tags_for(self.get_id(), derived=False)
      return self.tags

   def get_derived_tags(self):
      if not self.derived_tags:
         self.derived_tags = self.db.get_tags_for(self.get_id(), derived=True)
      return self.derived_tags

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

   def __str__(self):
      return self.get_name()

   def __repr__(self):
      return "movie: {}, stars: {}, tags: {}".format(self.mdict, self.get_stars(), self.get_tags())

class Star():
   def __init__(self, star_dict):
      self.name = star_dict["name"]
      self.id = star_dict["id"]

   def get_id(self):
      return self.id

   def get_name(self):
      return self.name

   def __str__(self):
      return self.get_name()

class Tag():
   def __init__(self, tag_dict):
      self.name = tag_dict["name"]
      self.id = tag_dict["id"]
      self.subsetof = tag_dict["subsetof"]

   def get_id(self):
      return self.id

   def get_name(self):
      return self.name

   def __str__(self):
      return self.get_name()
