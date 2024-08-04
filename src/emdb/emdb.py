from . import eeact
from . import database

import os
import subprocess as P
import shutil
from collections import deque
from threading import Semaphore, Lock
from functools import partial
import random
from backup_move import move_file
import asyncio
from hashlib import md5

# random io ###################################################################
async def play(path):
   proc = await asyncio.create_subprocess_exec(
      "mpv",
      path,
      stdout=asyncio.subprocess.DEVNULL,
      stdin=asyncio.subprocess.DEVNULL,
      stderr=asyncio.subprocess.DEVNULL
   )
   return await proc.wait() == 0

# commands from main widget ###################################################

async def remove_movie(man, sel):
   if not sel:
      return

   affirmative = await man.get_widget("infoPopup").show_question("Are you sure you want to delete this?")
   if not affirmative:
      man.get_widget("MAIN").focus()
      return

   sel.remove_self()
   move_file(os.path.join(man["ad"], sel.get_path()), man["td"])

   mainWid = man.get_widget("MAIN")
   mainWid.remove_selected()
   mainWid.focus()

async def add_inspection(man, sel):
   if not sel:
      return

   fut = man.get_widget("modifyMovieQuery").new_session()
   man.get_widget("modifyTitle").set_title(sel)

   if not await fut:
      man.get_widget("inspectionSelector").focus()
      return

   newPath = move_file(os.path.join(man["id"], sel), man["ad"])
   newName = os.path.basename(newPath)
   stars = [s.get_id() for s in man.get_widget("modifyMovieStars").get_highlighted()]
   tags = [t.get_id() for t in man.get_widget("modifyMovieTags").get_highlighted()]
   newMovie = man["db"].add_movie(newName, "", False, stars, tags)

   man.get_widget("MAIN").add(newMovie)

   insp = man.get_widget("inspectionSelector")
   insp.remove_selected()
   insp.focus()

async def start_inspection(man):
   # do not consider videos in dups
   dups = set()
   for cur, _, links in os.walk(man["dd"]):
      for l in links:
         fullpath = os.path.join(cur, l)
         if not os.path.islink(fullpath):
            continue
         link = os.readlink(fullpath)
         if os.path.isabs(link):
            continue
         dups.add(os.path.normpath(os.path.join(cur, link)))

   # check if candidates
   allCandidates = [full for buf in man["bd"]
                         for entry in os.scandir(buf)
                         for full in (entry.path,)
                         if full not in dups]
   if not allCandidates:
      await man.get_widget("infoPopup").show_info("No videos in buffer", severity=eeact.InfoPopup.ERROR)
      man.get_widget("MAIN").focus()
      return

   # pick, move and play a random one
   randChoice = random.choice(allCandidates)
   randChoice = move_file(randChoice, man["id"])
   man.get_widget("infoPopup").show_blocked("waiting for mpv...")
   await play(randChoice)
   man.refresh_event.set()

   # keep?
   keep = await man.get_widget("infoPopup").show_question("Want to keep?")
   if not keep:
      move_file(randChoice, man["td"])
      man.get_widget("MAIN").focus()
      return

   # choose stars and tags
   fut = man.get_widget("modifyMovieQuery").new_session()
   man.get_widget("modifyTitle").set_title(os.path.basename(randChoice))
   if not await fut:
      man.get_widget("MAIN").focus()
      return

   # add to db and stuff
   newPath = move_file(randChoice, man["ad"])
   newName = os.path.basename(newPath)
   stars = [s.get_id() for s in man.get_widget("modifyMovieStars").get_highlighted()]
   tags = [t.get_id() for t in man.get_widget("modifyMovieTags").get_highlighted()]
   newMovie = man["db"].add_movie(newName, "", False, stars, tags)

   # focus main
   mainWid = man.get_widget("MAIN")
   mainWid.add(newMovie)
   mainWid.focus()

async def modify_selected(man, sel):
   if not sel:
      return
   filename = sel.get_path()

   fut = man.get_widget("modifyMovieQuery").new_session()
   man.get_widget("modifyTitle").set_title(filename)
   man.get_widget("modifyMovieStars").highlight_by(lambda x: x in sel.get_stars())
   man.get_widget("modifyMovieTags").highlight_by(lambda x: x in sel.get_tags())

   man.refresh_event.set()
   ok = await fut

   if ok:
      stars = [s.get_id() for s in man.get_widget("modifyMovieStars").get_highlighted()]
      tags = [t.get_id() for t in man.get_widget("modifyMovieTags").get_highlighted()]
      sel.set_stars(stars)
      sel.set_tags(tags)

      man.get_widget("videoStats").update()
      man.get_widget("MAIN").focus()
   else:
      man.get_widget("MAIN").focus()

async def add_star(man):
   man.get_widget("inputTitle").set_title("Add new star")
   if not await man.get_widget("input").new_session():
      man.get_widget("MAIN").focus()
      return

   man.get_widget("MAIN").focus()
   inp = man.get_widget("input")
   val = inp.get_input()
   if val:
      man["db"].add_star(val)

async def add_tag(man):
   man.get_widget("inputTitle").set_title("Add new tag")
   if not await man.get_widget("input").new_session():
      man.get_widget("MAIN").focus()
      return

   man.get_widget("MAIN").focus()
   inp = man.get_widget("input")
   val = inp.get_input()
   if val:
      man["db"].add_tag(val)

async def set_name_selected(man, sel):
   if not sel:
      return

   man.get_widget("inputTitle").set_title("Set name")
   inp = man.get_widget("input")
   fut = inp.new_session()
   inp.set_initial_input(sel.get_disp())

   if not await fut:
      man.get_widget("MAIN").focus()
      return

   inp = man.get_widget("input")
   val = inp.get_input()
   sel.set_name(val)
   mai = man.get_widget("MAIN")
   mai.refresh()
   mai.focus()

def toggle_starred(man, sel):
   if not sel:
      return
   sel.set_starred(not sel.is_starred())
   man.get_widget("videoStats").update()

async def copy_selected(man, sel):
   if not sel:
      return
   try:
      from pyperclip import copy
      copy(sel.get_path())
   except ModuleNotFoundError:
      await man.get_widget("infoPopup").show_info("Can't find pyperclip", severity=eeact.InfoPopup.WARNING)
      man.get_widget("MAIN").focus()

async def selector_search(man):
   man.get_widget("inputTitle").set_title("Search for:")
   if not await man.get_widget("input").new_session():
      man.get_widget("MAIN").focus()
      return

   mai = man.get_widget("MAIN")
   mai.focus()
   inp = man.get_widget("input")
   val = inp.get_input()
   if val:
      try:
         sear = database.Search(val)
         mai.filter_by(sear.match)
      except database.Search.ParseError as e:
         await man.get_widget("infoPopup").show_info(str(e), severity=eeact.InfoPopup.ERROR)
         mai.focus()
   else:
      mai.clear_filter()

# widgets #####################################################################
class QuerySession():
   def __init__(self, manager):
      self.fut = None
      self.manager = manager
      self.key_help = {"ESC": "abort", "RET": "confirm"}

   def new_session(self):
      loop = asyncio.get_running_loop()
      self.fut = loop.create_future()
      return self.fut

   def key_event(self, key):
      if key == eeact.ca.NL:
         self.fut.set_result(True)
      elif key == eeact.ca.ESC:
         self.fut.set_result(False)
      else:
         return False
      return True

class StatsWidget(eeact.Widget):
   def __init__(self, name):
      super().__init__(name)
      self.values = []
      self.movie = None

   def set_movie(self, movie):
      if self.movie == movie:
         return
      self.movie = movie
      self.update()

   def clear(self):
      self.values.clear()
      self.movie = None
      self.touch()

   def update(self):
      self.touch()
      self._generate_string()

   def _generate_string(self):
      self.values.clear()
      tit = ["${stats_key}", "File: "]
      if self.movie.is_starred():
         tit.extend(["${stats_starred}", '*'])
      tit.extend(["$0", str(self.movie.get_path())])
      self.values.append(tit)
      starstr = ", ".join(s.get_name() for s in self.movie.get_stars())
      self.values.append(["${stats_key}", "Featured: ", "$0", starstr])
      tagsstr = ", ".join(s.get_name() for s in self.movie.get_tags())
      self.values.append(["${stats_key}", "Tags: ", "$0", tagsstr])
      self.values.append(["${stats_key}", "Added: ", "$0", str(self.movie.get_added_date())])

   def draw(self, win):
      win.erase()
      for i,v in enumerate(self.values):
         if i > self.h:
            break
         self.format_draw(win, 0, i, v)

class KeyHelpWidget(eeact.Widget):
   def __init__(self, name):
      super().__init__(name)
      self.key_helps = {}
      self.value = []
      self.value_len = 0

   def set_cur_keys(self, keys):
      self.key_helps = keys
      self._generate_help_string()
      self.touch()

   def _generate_help_string(self):
      if not self.key_helps:
         self.value = []
         self.value_len = 0
         return

      formstr = []

      for k,v in self.key_helps.items():
         formstr.extend(["${key_highlight}", k, ":$0 ", v, ", "])
      del formstr[-1]

      self.value_len, self.value = eeact.StringFormatter.parse_and_len(formstr, self.manager)

      if self.value_len > self.w:
         formstr = [", " if i % 5 == 2 else x for i,x in enumerate(formstr) if i % 5 <= 2]
         del formstr[-1]
         self.value_len, self.value = eeact.StringFormatter.parse_and_len(formstr, self.manager)

   def draw(self, win):
      win.erase()
      x = eeact.StringFormatter.calc_centered_pos(self.value_len, self.w)
      eeact.StringFormatter.draw_parsed(win, x, 0, self.value, dots=True)

class TitleWidget(eeact.Widget):
   def __init__(self, name):
      super().__init__(name)
      self.value = "title"

   def set_title(self, title):
      self.value = title
      self.touch()

   def draw(self, win):
      win.erase()
      self.format_draw(win, 0, 0, self.value, centered=True)

# NOTE: this is not fuzzy lol
class FuzzyFindList(eeact.SplitLayout):
   class FuzzyInput(eeact.InputWidget):
      def __init__(self, name, fList):
         super().__init__(name)
         self.fList = fList
         self.key_help = {"SPC": "select", "<down>": "next", "<up>": "previous"}

      def changed(self):
         s = self.get_input()
         def fuzzy(x):
            name = x.get_name().lower()
            return s in name

         sortfun = fuzzy if self.get_input() else lambda x: True
         self.fList.filter_by(sortfun)

      def key_event(self, key):
         if key != eeact.ca.SP:
            if super().key_event(key):
               return True

         if key == eeact.curses.KEY_DOWN:
            self.fList.next()
         elif key == eeact.curses.KEY_UP:
            self.fList.prev()
         elif key == eeact.ca.SP:
            self.fList.highlight()
         else:
            return False
         return True

      def draw(self, win):
         if not self.is_focused:
            self.manager.push_attr_override("input_cursor", 0)
         super().draw(win)
         if not self.is_focused:
            self.manager.pop_attr_override()

   class FuzzyList(eeact.ListWidget):
      pass

   def __init__(self, name):
      self.fList = self.FuzzyList("{}_fuzzyList".format(name))
      self.fInput = self.FuzzyInput("{}_fuzzyInput".format(name), self.fList)
      super().__init__(
         name,
         self.Alignment.VERTICAL,
         eeact.BorderWrapperLayout("b", self.fInput), 2,
         self.fList, 0.0
      )

   def focus(self):
      self.fInput.focus()

   def set_list(self, l):
      self.fInput.clear()
      self.fList.set_list(l)
      self.fList.sort_by(lambda s: s.get_name().lower())
      self.fList.goto_first()

   def highlight_by(self, pred):
      self.fList.highlight_by(pred)

   def get_highlighted(self):
      return self.fList.get_highlighted()

class ModifyStarsWidget(FuzzyFindList):
   def __init__(self, name):
      super().__init__(name)
      self.key_help = {
         "TAB": "goto tags"
      }

   def key_event(self, key):
      if super().key_event(key):
         return True

      if key == eeact.ca.TAB:
         self.manager.get_widget("modifyMovieTags").focus()
      else:
         return False
      return True

   def clear(self):
      self.set_list(self.manager["db"].get_stars())

class ModifyTagsWidget(FuzzyFindList):
   def __init__(self, name):
      super().__init__(name)
      self.key_help = {
         "TAB": "goto stars"
      }

   def key_event(self, key):
      if super().key_event(key):
         return True

      if key == eeact.ca.TAB:
         self.manager.get_widget("modifyMovieStars").focus()
      else:
         return False
      return True

   def clear(self):
      self.set_list(self.manager["db"].get_tags())

class ModifyMovieQuery(eeact.WrapperLayout, QuerySession):
   def __init__(self, name, widget):
      eeact.WrapperLayout.__init__(self, name, widget)
      QuerySession.__init__(self, self.manager)

   def new_session(self):
      fut = super().new_session()
      stars = self.manager.get_widget("modifyMovieStars")
      stars.clear()
      stars.focus()
      self.manager.get_widget("modifyMovieTags").clear()
      return fut

   def key_event(self, key):
      if eeact.WrapperLayout.key_event(self, key):
         return True
      if QuerySession.key_event(self, key):
         return True
      return False

class GlobalBindings(eeact.WrapperLayout):
   def __init__(self, name, widget):
      super().__init__(name, widget)
      self.key_help = {"q": "exit"}

   def key_event(self, key):
      if key == ord('q'):
         self.manager.stop()
         return True
      return False

class SelectorWidget(eeact.FancyListWidget):
   def __init__(self, name):
      super().__init__(name)
      self.key_help = {
         "jkgG": "vim",
         "l": "play",
         "i": "inspect new",
         "p": "add star",
         "t": "add tag",
         "s": "toggle star",
         "m": "modify",
         "y": "copy path",
         "n": "set name",
         "TAB": "goto inspection",
         "f": "search",
         "r": "random",
         "d": "delete"
      }
      self.sort_functions = deque([
         lambda a,b: a.get_disp().lower() < b.get_disp().lower(),
         lambda a,b: a.get_disp().lower() >= b.get_disp().lower(),
         lambda a,b: a.get_added_date() >= b.get_added_date(),
         lambda a,b: a.get_added_date() < b.get_added_date(),
         lambda a,b: int(a.is_starred()) > int(b.is_starred())
      ])
      self.sort_names = deque([
         "n↓",
         "n↑",
         "dn",
         "do",
         "*"
      ])

   def sort_next(self):
      class Cmp():
         def __init__(self, m, f):
            self.f = f
            self.m = m
         def __lt__(self, other):
            return self.f(self.m, other.m)

      sf = self.sort_functions[0]
      self.sort_by(lambda m: Cmp(m, sf))
      self.sort_functions.rotate(-1)

      self.key_help["o"] = self.sort_names[0]
      self.sort_names.rotate(-1)

   def init(self):
      self.set_list(self.manager["db"].get_movies(lazy=False))
      self.sort_next()
      self.goto_first()

   def _play_selected(self):
      sel = self.get_selected()
      if not sel:
         return
      asyncio.create_task(play(os.path.join(self.manager["ad"], sel.get_path())))

   def key_event(self, key):
      if key != eeact.ca.SP and super().key_event(key):
         return True

      if key == ord('i'):
         asyncio.create_task(start_inspection(self.manager))
      elif key == ord('d'):
         sel = self.get_selected()
         if sel:
            asyncio.create_task(remove_movie(self.manager, sel))
      elif key == ord('p'):
         asyncio.create_task(add_star(self.manager))
      elif key == ord('t'):
         asyncio.create_task(add_tag(self.manager))
      elif key == ord('o'):
         self.sort_next()
      elif key == ord('s'):
         toggle_starred(self.manager, self.get_selected())
      elif key == ord('l') or key == eeact.curses.KEY_RIGHT:
         self._play_selected()
      elif key == ord('m'):
         asyncio.create_task(modify_selected(self.manager, self.get_selected()))
      elif key == ord('y'):
         asyncio.create_task(copy_selected(self.manager, self.get_selected()))
      elif key == ord('n'):
         asyncio.create_task(set_name_selected(self.manager, self.get_selected()))
      elif key == eeact.ca.TAB:
         self.manager.get_widget("inspectionSelector").focus()
      elif key == ord('f'):
         asyncio.create_task(selector_search(self.manager))
      elif key == ord('r'):
         self.goto_random()
         self._play_selected()
      else:
         return False
      return True

class InspectionSelectorWidget(eeact.FancyListWidget):
   def __init__(self, name):
      super().__init__(name)
      self.key_help = {
         "jkgG": "vim",
         "l": "play",
         "TAB": "goto main",
         "a": "add",
         "d": "trash"
      }

   def key_event(self, key):
      if key != eeact.ca.SP and super().key_event(key):
         return True

      if key == eeact.ca.TAB:
         self.manager.get_widget("MAIN").focus()
      elif key == ord('l'):
         sel = self.get_selected()
         if not sel:
            return
         asyncio.create_task(play(os.path.join(self.manager["id"], sel)))
      elif key == ord('a'):
         asyncio.create_task(add_inspection(self.manager, self.get_selected()))
      elif key == ord('d'):
         sel = self.get_selected()
         if sel:
            self.remove_selected()
            move_file(os.path.join(self.manager["id"], sel), self.manager["td"])
      else:
         return False
      return True

   def onfocus(self):
      self.set_list(os.listdir(self.manager["id"]))

class PreviewWidget(eeact.ImageWidget):
   def __init__(self, name):
      super().__init__(name)
      self.movie_path = None
      self.thumb_exec = "ffmpegthumbnailer"
      self.task = None

   def _hash_name(self, path):
      m = md5()
      # m.update(self.manager["cd"].encode())
      m.update(path.encode())
      cachename = m.hexdigest() + ".jpg"
      cachename = os.path.join(self.manager["cd"], cachename)
      return cachename

   def preview(self, movie_path):
      if self.movie_path == movie_path:
         return
      self.movie_path = movie_path

      if movie_path is None:
         self.clear_image()
         return

      cachename = self._hash_name(movie_path)
      if os.path.isfile(cachename):
         self.set_image(cachename)
      else:
         self.clear_image()
         if self.task is None or self.task.done():
            self.task = asyncio.create_task(self._start_thumbnailer(self.movie_path))

   async def _start_thumbnailer(self, movie_path):
      if not shutil.which(self.thumb_exec):
         return

      cachename = self._hash_name(movie_path)

      if os.path.isfile(cachename):
         return

      proc = await asyncio.create_subprocess_exec(
         self.thumb_exec,
         "-i", movie_path,
         "-o", cachename,
         "-s", "0",
         stdout=asyncio.subprocess.DEVNULL,
         stdin=asyncio.subprocess.DEVNULL,
         stderr=asyncio.subprocess.DEVNULL
      )
      await proc.wait()

      if self.movie_path == movie_path:
         self.set_image(cachename)
         self.manager.refresh_event.set()
      else:
         await self._start_thumbnailer(self.movie_path)

class MyInputWidget(eeact.InputWidget, QuerySession):
   def __init__(self, name):
      eeact.InputWidget.__init__(self, name)
      QuerySession.__init__(self, self.manager)

   def new_session(self):
      fut = super().new_session()
      self.clear()
      self.focus()
      return fut

   def key_event(self, key):
      if eeact.InputWidget.key_event(self, key):
         return True
      if QuerySession.key_event(self, key):
         return True
      return False

# globals #####################################################################

def global_key_help_hook(man):
   # haxxa in key_help
   infoPopup = man.get_widget("infoPopup_InfoWidget")
   if infoPopup.kind == eeact.InfoPopup.YESNO:
      infoPopup.key_help = {"y": "yes", "n": "no"}
   elif infoPopup.kind == eeact.InfoPopup.OKESC:
      infoPopup.key_help = {"RET/y": "ok"}
   else:
      infoPopup.key_help = {}
   infoPopup.key_help.update({k:"" for k in man.get_widget("globals").key_help})

   keys = {}
   def map_fun(wid, *_, **__):
      if hasattr(wid, "key_help"):
         keys.update(wid.key_help)

   man.map_focused(map_fun)
   keys = {k:v for k,v in keys.items() if v}
   kh = man.get_widget("keyHelp")
   kh.set_cur_keys(keys)

def update_stats(man):
   mai = man.get_widget("MAIN")
   ins = man.get_widget("inspectionSelector")
   if not mai.is_hidden() and mai.get_selected():
      man.get_widget("videoStats").set_movie(mai.get_selected())
      man.get_widget("img").preview(os.path.join(man["ad"], mai.get_selected().get_path()))
   elif not ins.is_hidden() and ins.get_selected():
      man.get_widget("videoStats").clear()
      man.get_widget("img").preview(os.path.join(man["id"], ins.get_selected()))
   else:
      man.get_widget("img").preview(None)

# main ########################################################################

def start(dbfile, archivedir, bufferdirs, inspectdir, cachedir, trashdir, dupdir):
   l = GlobalBindings(
      "globals",
      eeact.InfoPopup(
         "infoPopup",
         eeact.PopupLayout(
            "inputPopup",
            eeact.PopupLayout(
               "modifyMoviePopup",
               eeact.SplitLayout(
                  "keyMainLayout",
                  eeact.SplitLayout.Alignment.VERTICAL,
                  eeact.ConstraintLayout(
                     eeact.BorderWrapperLayout(
                        "lrt34",
                        eeact.SplitLayout(
                           "mainLayout",
                           eeact.SplitLayout.Alignment.VERTICAL,
                           eeact.SplitLayout(
                              "mainMiddleLayout",
                              eeact.SplitLayout.Alignment.HORIZONTAL,
                              eeact.TabbedLayout(
                                 "selectorTab",
                                 SelectorWidget("MAIN"),
                                 InspectionSelectorWidget("inspectionSelector")
                              ), 0.3,
                              eeact.BorderWrapperLayout(
                                 "l",
                                 PreviewWidget("img")
                              ), 0.0
                           ), 0.0,
                           eeact.BorderWrapperLayout(
                              "tb",
                              StatsWidget("videoStats")
                           ), 6
                        )
                     ),
                     maxw=120
                  ), 0.0,
                  KeyHelpWidget("keyHelp"), 1
               ),
               eeact.ConstraintLayout(
                  eeact.BorderWrapperLayout(
                     "tblr",
                     eeact.SplitLayout(
                        "modifyMovieLayout1",
                        eeact.SplitLayout.Alignment.VERTICAL,
                        eeact.BorderWrapperLayout(
                           "b",
                           TitleWidget("modifyTitle")
                        ), 2,
                        ModifyMovieQuery(
                           "modifyMovieQuery",
                           eeact.SplitLayout(
                              "modifyMovieLayout2",
                              eeact.SplitLayout.Alignment.HORIZONTAL,
                              eeact.BorderWrapperLayout(
                                 "r",
                                 ModifyStarsWidget("modifyMovieStars")
                              ), 0.5,
                              ModifyTagsWidget("modifyMovieTags"), 0.0
                           )
                        ), 0.0
                     )
                  ),
                  maxh=15,
                  maxw=50
               )
            ),
            eeact.ConstraintLayout(
               eeact.BorderWrapperLayout(
                  "tblr",
                  eeact.SplitLayout(
                     "inputLayout1",
                     eeact.SplitLayout.Alignment.VERTICAL,
                     TitleWidget("inputTitle"), 1,
                     MyInputWidget("input"), 0.0
                  )
               ),
               maxh=4,
               maxw=50
            )
         ),
         50,
         8
      )
   )

   man = eeact.Manager(l)

   man.init_color(1, eeact.curses.COLOR_RED, -1)
   man.init_color(2, eeact.curses.COLOR_BLUE, -1)
   man.init_color(3, eeact.curses.COLOR_MAGENTA, -1)
   man.init_color(4, eeact.curses.COLOR_YELLOW, -1)
   man.add_color("key_highlight", 2)
   man.add_color("fancy_list_arrow", 1)
   man.add_color("list_highlight", 1)
   man.add_color("stats_key", 3)
   man.add_color("stats_starred", 4)
   man.add_attr("input_cursor", eeact.curses.A_REVERSE)
   man.add_color("info_info", 2)
   man.add_color("info_warning", 4)
   man.add_color("info_error", 1)
   man.add_color("info_block", 1)
   man.on_any_event(global_key_help_hook)
   man.on_any_event(update_stats)
   man["id"] = inspectdir
   man["ad"] = archivedir
   man["bd"] = bufferdirs
   man["cd"] = cachedir
   man["td"] = trashdir
   man["dd"] = dupdir

   from contextlib import closing
   with closing(database.Database(dbfile)) as db:
      man["db"] = db
      man.start(ueber=True)

