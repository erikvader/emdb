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

# commands from main widget ###################################################

def start_inspection(man):
   allCandidates = os.listdir(man["bd"])
   aclen = len(allCandidates)
   if aclen <= 0:
      # TODO: show a popup or something instead of crashing
      raise Exception("tomt")

   import random
   randChoice = allCandidates[random.randrange(len(allCandidates))]

   # randChoice = move_file(randChoice, man["bd"], man["id"])

   # import subprocess as P
   # P.run(["mpv", os.path.join(man["id"], randChoice)], stdout=P.DEVNULL, stdin=P.DEVNULL, stderr=P.DEVNULL)

   def err(manager):
      manager.get_widget("MAIN").focus()

   def succ(manager):
      pass

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
      self.value = "stats here plz"

   def draw(self, win):
      if self.resized:
         win.erase()
      win.addstr(0, 0, self.value)

class KeyHelpWidget(interface.Widget):
   def __init__(self, name):
      super().__init__(name)
      self.key_helps = {}
      self.value = ""

   def set_cur_keys(self, keys):
      self.key_helps = keys
      self.touch()
      self.resized = True # haxx to make it erase in self.draw()

   def _generate_help_string(self):
      self.value = ""
      totallen = 0
      for k,v in self.key_helps.items():
         totallen += len(": ") + len(k) + len(v) + len(", ")
      totallen -= len(", ")

      if totallen <= self.w:
         for k,v in self.key_helps.items():
            self.value += r"${{key_highlight}}{}$0: {}, ".format(k, v)
         self.value = self.value[:-2]
      else:
         for k in self.key_helps:
            self.value += k + ", "
         self.value = self.value[:-2]

   def draw(self, win):
      if self.resized:
         win.erase()
         self._generate_help_string()
      self.draw_formatted(win, 0, 0, self.value)

class TitleWidget(interface.Widget):
   def __init__(self, name):
      super().__init__(name)
      self.value = "title"

   def set_title(self, title):
      self.value = title
      self.resized = True # haxx to force draw to clear
      self.touch()

   def draw(self, win):
      if self.resized:
         win.erase()
      x = max(0, (self.w - len(self.value)) // 2)
      interface.ice(win.addnstr, 0, x, self.value, self.w)

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
         "i": "inspect new",
         "p": "add star",
         "t": "add tag"
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

# main ########################################################################

def start(dbfile, archivedir, bufferdir, inspectdir):
   l = GlobalBindings(
      "globals",
      interface.PopupLayout(
         "inputPopup",
         interface.PopupLayout(
            "modifyMoviePopup",
            interface.ConstraintLayout(
               interface.BorderWrapperLayout(
                  "lrt",
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
                     ), 0.15,
                     KeyHelpWidget("keyHelp"), 1
                  )
               ),
               maxw=120
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
   man.add_color("key_highlight", 2)
   man.add_color("fancy_list_arrow", 1)
   man.add_color("list_highlight", 1)
   man.on_any_event(global_key_help_hook)

   db = database.Database(dbfile)
   man["db"] = db
   man["id"] = inspectdir
   man["ad"] = archivedir
   man["bd"] = bufferdir

   man.start()
   man["db"].close()

