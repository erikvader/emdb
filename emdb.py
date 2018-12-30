#!/bin/python

"""
optional dependenies: pyperclip
"""

from . import interface
from . import database

import os
import subprocess as P
import shutil

# random io ###################################################################
def move_file (f, src, dest):
   num = 1
   s = os.path.join(src, f)
   if not (os.path.exists(s)):
      raise Exception("Couldn't copy:", s, "Is the name too long maybe?")
   new_f = f
   d = os.path.join(dest, f)
   while os.path.exists(d):
      new_f = str(num) + "_" + f
      d = os.path.join(dest, new_f)
      num += 1
   shutil.move(s, d)
   return new_f

def play(path):
   P.run(["mpv", path], stdout=P.DEVNULL, stdin=P.DEVNULL, stderr=P.DEVNULL)

# commands from main widget ###################################################

def start_inspection(man):
   allCandidates = os.listdir(man["bd"])
   aclen = len(allCandidates)
   if aclen <= 0:
      man.get_widget("infoPopup").show_info("No videos in buffer", kind=interface.InfoPopup.ERROR)
      return

   import random
   randChoice = allCandidates[random.randrange(len(allCandidates))]

   randChoice = move_file(randChoice, man["bd"], man["id"])
   play(os.path.join(man["id"], randChoice))

   def err(manager):
      manager.get_widget("MAIN").focus()

   def succ(manager):
      newName = move_file(randChoice, man["id"], man["ad"])
      stars = [s.get_id() for s in manager.get_widget("modifyMovieStars").get_highlighted()]
      tags = [t.get_id() for t in manager.get_widget("modifyMovieTags").get_highlighted()]
      newMovie = man["db"].add_movie(newName, "", False, stars, tags)

      mainWid = manager.get_widget("MAIN")
      mainWid.add(newMovie)
      mainWid.focus()

   man.get_widget("modifyMovieQuery").new_session(on_error=err, on_success=succ)
   man.get_widget("modifyTitle").set_title(randChoice)

def modify_selected(man, sel):
   if not sel:
      return
   filename = sel.get_path()

   def err(manager):
      manager.get_widget("MAIN").focus()

   def succ(manager):
      stars = [s.get_id() for s in manager.get_widget("modifyMovieStars").get_highlighted()]
      tags = [t.get_id() for t in manager.get_widget("modifyMovieTags").get_highlighted()]
      sel.set_stars(stars)
      sel.set_tags(tags)

      manager.get_widget("videoStats").update()
      manager.get_widget("MAIN").focus()

   man.get_widget("modifyMovieQuery").new_session(on_error=err, on_success=succ)
   man.get_widget("modifyTitle").set_title(filename)
   man.get_widget("modifyMovieStars").highlight_by(lambda x: x in sel.get_stars())
   man.get_widget("modifyMovieTags").highlight_by(lambda x: x in sel.get_tags())

def add_star(man):
   def err(manager):
      manager.get_widget("MAIN").focus()
   def succ(manager):
      manager.get_widget("MAIN").focus()
      inp = manager.get_widget("input")
      val = inp.get_input()
      if val:
         inp.manager["db"].add_star(val)

   man.get_widget("inputTitle").set_title("Add new star")
   man.get_widget("input").new_session(on_error=err, on_success=succ)

def add_tag(man):
   def err(manager):
      manager.get_widget("MAIN").focus()
   def succ(manager):
      manager.get_widget("MAIN").focus()
      inp = manager.get_widget("input")
      val = inp.get_input()
      if val:
         inp.manager["db"].add_tag(val)

   man.get_widget("inputTitle").set_title("Add new tag")
   man.get_widget("input").new_session(on_error=err, on_success=succ)

def toggle_starred(man, sel):
   if not sel:
      return
   sel.set_starred(not sel.is_starred())
   man.get_widget("videoStats").update()

def play_selected(man, sel):
   if not sel:
      return
   play(os.path.join(man["ad"], sel.get_path()))

def copy_selected(man, sel):
   if not sel:
      return
   try:
      from pyperclip import copy
      copy(sel.get_path())
   except ModuleNotFoundError:
      man.get_widget("infoPopup").show_info("Can't find pyperclip", kind=interface.InfoPopup.WARNING)

# widgets #####################################################################
class QuerySession():
   def __init__(self, manager):
      self.on_success = lambda _: None
      self.on_error = lambda _: None
      self.manager = manager
      self.key_help = {"ESC": "abort", "RET": "confirm"}

   def new_session(self, on_success=None, on_error=None):
      self.on_success = on_success if on_success else lambda s: None
      self.on_error = on_error if on_error else lambda s: None

   def key_event(self, key):
      if key == interface.ca.NL:
         self.on_success(self.manager)
      elif key == interface.ca.ESC:
         self.on_error(self.manager)
      else:
         return False
      return True

class StatsWidget(interface.Widget):
   def __init__(self, name):
      super().__init__(name)
      self.values = []
      self.movie = None

   def set_movie(self, movie):
      if self.movie == movie:
         return
      self.movie = movie
      self.update()

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

class KeyHelpWidget(interface.Widget):
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
      formstr = []

      for k,v in self.key_helps.items():
         formstr.extend(["${key_highlight}", k, ":$0 ", v, ", "])
      del formstr[-1]

      self.value_len, self.value = interface.StringFormatter.parse_and_len(formstr, self.manager)

      if self.value_len > self.w:
         formstr = [", " if i % 5 == 2 else x for i,x in enumerate(formstr) if i % 5 <= 2]
         del formstr[-1]
         self.value_len, self.value = interface.StringFormatter.parse_and_len(formstr, self.manager)

   def draw(self, win):
      win.erase()
      x = interface.StringFormatter.calc_centered_pos(self.value_len, self.w)
      interface.StringFormatter.draw_parsed(win, x, 0, self.value, dots=True)

class TitleWidget(interface.Widget):
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
class FuzzyFindList(interface.SplitLayout):
   class FuzzyInput(interface.InputWidget):
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
         if key != interface.ca.SP:
            if super().key_event(key):
               return True

         if key == interface.curses.KEY_DOWN:
            self.fList.next()
         elif key == interface.curses.KEY_UP:
            self.fList.prev()
         elif key == interface.ca.SP:
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

   class FuzzyList(interface.ListWidget):
      pass

   def __init__(self, name):
      self.fList = self.FuzzyList("{}_fuzzyList".format(name))
      self.fInput = self.FuzzyInput("{}_fuzzyInput".format(name), self.fList)
      super().__init__(
         name,
         self.Alignment.VERTICAL,
         interface.BorderWrapperLayout("b", self.fInput), 2,
         self.fList, 0.0
      )

   def focus(self):
      self.fInput.focus()

   def set_list(self, l):
      self.fInput.clear()
      self.fList.set_list(l)

   def sort_by(self, pred):
      self.fList.sort_by(pred)

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

      if key == interface.ca.TAB:
         self.manager.get_widget("modifyMovieTags").focus()
      else:
         return False
      return True

   def clear(self):
      self.set_list(self.manager["db"].get_stars())
      self.sort_by(lambda s: s.get_name().lower())

class ModifyTagsWidget(FuzzyFindList):
   def __init__(self, name):
      super().__init__(name)
      self.key_help = {
         "TAB": "goto stars"
      }

   def key_event(self, key):
      if super().key_event(key):
         return True

      if key == interface.ca.TAB:
         self.manager.get_widget("modifyMovieStars").focus()
      else:
         return False
      return True

   def clear(self):
      self.set_list(self.manager["db"].get_tags())
      self.sort_by(lambda t: t.get_name().lower())

class ModifyMovieQuery(interface.WrapperLayout, QuerySession):
   def __init__(self, name, widget):
      interface.WrapperLayout.__init__(self, name, widget)
      QuerySession.__init__(self, self.manager)

   def new_session(self, on_success=None, on_error=None):
      super().new_session(on_success, on_error)
      stars = self.manager.get_widget("modifyMovieStars")
      stars.clear()
      stars.focus()
      self.manager.get_widget("modifyMovieTags").clear()

   def key_event(self, key):
      if interface.WrapperLayout.key_event(self, key):
         return True
      if QuerySession.key_event(self, key):
         return True
      return False

class GlobalBindings(interface.WrapperLayout):
   def __init__(self, name, widget):
      super().__init__(name, widget)
      self.key_help = {"ESC": "exit"}

   def key_event(self, key):
      if key == interface.ca.ESC:
         self.manager.stop()

class SelectorWidget(interface.FancyListWidget):
   def __init__(self, name):
      super().__init__(name)
      self.key_help = {
         "j/<down>": "move down",
         "k/<up>": "move up",
         "l/<right>": "play",
         "i": "inspect new",
         "p": "add star",
         "t": "add tag",
         "s": "toggle star",
         "m": "modify",
         "y": "copy path"
      }

   def init(self):
      self.set_list(self.manager["db"].get_movies())

   def key_event(self, key):
      if super().key_event(key):
         return True

      if key == ord('i'):
         start_inspection(self.manager)
      elif key == ord('p'):
         add_star(self.manager)
      elif key == ord('t'):
         add_tag(self.manager)
      elif key == ord('o'):
         self.sort_by(lambda x: x.get_path())
      elif key == ord('s'):
         toggle_starred(self.manager, self.get_selected())
      elif key == ord('l') or key == interface.curses.KEY_RIGHT:
         play_selected(self.manager, self.get_selected())
      elif key == ord('m'):
         modify_selected(self.manager, self.get_selected())
      elif key == ord('y'):
         copy_selected(self.manager, self.get_selected())
      else:
         return False
      return True

class PreviewWidget(interface.ImageWidget):
   def __init__(self, name):
      super().__init__(name)
      self.movie = None

   def init(self):
      pass
      # self.set_image("/home/erik/Pictures/PFUDOR_2.jpg")

   def preview(self, movie):
      if self.movie == movie:
         return
      self.movie = movie
      thumb = "ffmpegthumbnailer"
      if not shutil.which(thumb):
         return

      cachename, _ = os.path.splitext(os.path.join(self.manager["cd"], self.movie.get_path()))
      cachename += ".jpg"

      if not os.path.isfile(cachename):
         P.run([
            thumb,
            "-i",
            # TODO: can vary, fix somehow
            os.path.join(self.manager["ad"], self.movie.get_path()),
            "-o",
            cachename,
            "-s", "0"
         ])

      self.set_image(cachename)

class MyInputWidget(interface.InputWidget, QuerySession):
   def __init__(self, name):
      interface.InputWidget.__init__(self, name)
      QuerySession.__init__(self, self.manager)

   def new_session(self, on_success=None, on_error=None):
      super().new_session(on_success, on_error)
      self.clear()
      self.focus()

   def key_event(self, key):
      if interface.InputWidget.key_event(self, key):
         return True
      if QuerySession.key_event(self, key):
         return True
      return False

# globals #####################################################################

def global_key_help_hook(man):
   # haxxa in key_help
   infoPopup = man.get_widget("infoPopup_InfoWidget")
   if infoPopup.yesno:
      infoPopup.key_help = {"ESC": "", "y": "yes", "n": "no"}
   else:
      infoPopup.key_help = {"ESC": "", "RET/y": "ok"}

   keys = {}
   def map_fun(wid, *_, **__):
      if hasattr(wid, "key_help"):
         keys.update(wid.key_help)

   man.map_focused(map_fun)
   keys = {k:v for k,v in keys.items() if v}
   kh = man.get_widget("keyHelp")
   kh.set_cur_keys(keys)

def update_stats(man):
   sel = man.get_widget("MAIN")
   if sel.get_selected():
      man.get_widget("videoStats").set_movie(sel.get_selected())
      man.get_widget("img").preview(sel.get_selected())

# main ########################################################################

def start(dbfile, archivedir, bufferdir, inspectdir, cachedir):
   l = GlobalBindings(
      "globals",
      interface.InfoPopup(
         "infoPopup",
         interface.PopupLayout(
            "inputPopup",
            interface.PopupLayout(
               "modifyMoviePopup",
               interface.SplitLayout(
                  "keyMainLayout",
                  interface.SplitLayout.Alignment.VERTICAL,
                  interface.ConstraintLayout(
                     interface.BorderWrapperLayout(
                        "lrt34",
                        interface.SplitLayout(
                           "mainLayout",
                           interface.SplitLayout.Alignment.VERTICAL,
                           interface.SplitLayout(
                              "mainMiddleLayout",
                              interface.SplitLayout.Alignment.HORIZONTAL,
                              SelectorWidget("MAIN"), 0.3,
                              interface.BorderWrapperLayout(
                                 "l",
                                 PreviewWidget("img")
                              ), 0.0
                           ), 0.0,
                           interface.BorderWrapperLayout(
                              "tb",
                              StatsWidget("videoStats")
                           ), 6
                        )
                     ),
                     maxw=120
                  ), 0.0,
                  KeyHelpWidget("keyHelp"), 1
               ),
               interface.ConstraintLayout(
                  interface.BorderWrapperLayout(
                     "tblr",
                     interface.SplitLayout(
                        "modifyMovieLayout1",
                        interface.SplitLayout.Alignment.VERTICAL,
                        interface.BorderWrapperLayout(
                           "b",
                           TitleWidget("modifyTitle")
                        ), 2,
                        ModifyMovieQuery(
                           "modifyMovieQuery",
                           interface.SplitLayout(
                              "modifyMovieLayout2",
                              interface.SplitLayout.Alignment.HORIZONTAL,
                              interface.BorderWrapperLayout(
                                 "r",
                                 ModifyStarsWidget("modifyMovieStars")
                              ), 0.5,
                              ModifyTagsWidget("modifyMovieTags"), 0.0
                           )
                        ), 0.0
                     )
                  ),
                  maxh=10,
                  maxw=50
               )
            ),
            interface.ConstraintLayout(
               interface.BorderWrapperLayout(
                  "tblr",
                  interface.SplitLayout(
                     "inputLayout1",
                     interface.SplitLayout.Alignment.VERTICAL,
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

   with interface.Manager(l) as man:
      man.init_color(1, interface.curses.COLOR_RED, -1)
      man.init_color(2, interface.curses.COLOR_BLUE, -1)
      man.init_color(3, interface.curses.COLOR_MAGENTA, -1)
      man.init_color(4, interface.curses.COLOR_YELLOW, -1)
      man.add_color("key_highlight", 2)
      man.add_color("fancy_list_arrow", 1)
      man.add_color("list_highlight", 1)
      man.add_color("stats_key", 3)
      man.add_color("stats_starred", 4)
      man.add_attr("input_cursor", interface.curses.A_REVERSE)
      man.add_color("info_info", 2)
      man.add_color("info_warning", 4)
      man.add_color("info_error", 1)
      man.on_any_event(global_key_help_hook)
      man.on_any_event(update_stats)
      man["id"] = inspectdir
      man["ad"] = archivedir
      man["bd"] = bufferdir
      man["cd"] = cachedir

      from contextlib import closing
      with closing(database.Database(dbfile)) as db:
         man["db"] = db
         man.start()

