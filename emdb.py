#!/bin/python

from . import interface
from . import database

import os

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
   import shutil
   shutil.move(s, d)
   return new_f

def play(path):
   import subprocess as P
   P.run(["mpv", path], stdout=P.DEVNULL, stdin=P.DEVNULL, stderr=P.DEVNULL)

# commands from main widget ###################################################

def start_inspection(man):
   allCandidates = os.listdir(man["bd"])
   aclen = len(allCandidates)
   if aclen <= 0:
      # TODO: show a popup or something instead of crashing
      raise Exception("tomt")

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
      if self.resized:
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

class ModifyStarsWidget(interface.ListWidget):
   def __init__(self, name):
      super().__init__(name)
      self.key_help = {
         "j/<down>": "move down",
         "k/<up>": "move up",
         "space": "select",
         "TAB": "goto other"
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

class ModifyTagsWidget(interface.ListWidget):
   def __init__(self, name):
      super().__init__(name)
      self.key_help = {
         "j/<down>": "move down",
         "k/<up>": "move up",
         "space": "select",
         "TAB": "goto other"
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
      # elif key == interface.ca.TAB:
      #    self.manager.get_widget("input").focus()

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
         "s": "toggle star"
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
      else:
         return False
      return True

class PreviewWidget(interface.ImageWidget):
   def init(self):
      pass
      # self.set_image("/home/erik/Pictures/PFUDOR_2.jpg")

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
   keys = {}
   def map_fun(wid, *_, **__):
      if hasattr(wid, "key_help"):
         keys.update(wid.key_help)

   man.map_focused(map_fun)
   kh = man.get_widget("keyHelp")
   kh.set_cur_keys(keys)

def update_stats(man):
   sel = man.get_widget("MAIN")
   if sel.get_selected():
      man.get_widget("videoStats").set_movie(sel.get_selected())

# main ########################################################################

def start(dbfile, archivedir, bufferdir, inspectdir):
   l = GlobalBindings(
      "globals",
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
                     TitleWidget("modifyTitle"), 1,
                     ModifyMovieQuery(
                        "modifyMovieQuery",
                        interface.SplitLayout(
                           "modifyMovieLayout2",
                           interface.SplitLayout.Alignment.HORIZONTAL,
                           ModifyStarsWidget("modifyMovieStars"), 0.5,
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
      )
   )

   man = interface.Manager(l)
   man.init_color(1, interface.curses.COLOR_RED, -1)
   man.init_color(2, interface.curses.COLOR_BLUE, -1)
   man.init_color(3, interface.curses.COLOR_MAGENTA, -1)
   man.init_color(4, interface.curses.COLOR_YELLOW, -1)
   man.add_color("key_highlight", 2)
   man.add_color("fancy_list_arrow", 1)
   man.add_color("list_highlight", 1)
   man.add_color("stats_key", 3)
   man.add_color("stats_starred", 4)
   man.on_any_event(global_key_help_hook)
   man.on_any_event(update_stats)

   db = database.Database(dbfile)
   man["db"] = db
   man["id"] = inspectdir
   man["ad"] = archivedir
   man["bd"] = bufferdir

   man.start()
   man["db"].close()

