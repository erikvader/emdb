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

   man.get_widget("modifyMoviePopup").show_popup()

# widgets #####################################################################
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

   def draw(self, win):
      if self.resized:
         win.erase()
      win.addstr(0, (self.w - len(self.value)) // 2, self.value)

class ModifyStarsWidget(interface.ListWidget):
   pass

class ModifyTagsWidget(interface.ListWidget):
   pass

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
      self.key_help = {"j/<down>": "move down", "k/<up>": "move up", "i": "inspect new"}

   def init(self):
      self.set_list(self.manager["db"].get_movies())

   def key_event(self, key):
      if key == interface.curses.KEY_DOWN or key == ord('j'):
         self.next()
         # self.manager.get_widget("img").touch()
      elif key == interface.curses.KEY_UP or key == ord('k'):
         self.prev()
         # self.manager.get_widget("img").touch()
      elif key == ord('i'):
         start_inspection(self.manager)
      else:
         return False
      return True

class PreviewWidget(interface.ImageWidget):
   def init(self):
      pass
      # self.set_image("/home/erik/Pictures/PFUDOR_2.jpg")

class MyInputWidget(interface.InputWidget):
   pass

# globals #####################################################################

def global_key_help_hook(man):
   kh = man.get_widget("keyHelp")
   gl = man.get_widget("globals")
   fo = man.current_focus
   fo_keys = {}
   if hasattr(fo, "key_help"):
      fo_keys = fo.key_help
   kh.set_cur_keys({**gl.key_help, **fo_keys})

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
                     interface.SplitLayout(
                        "modifyMovieLayout2",
                        interface.SplitLayout.Alignment.HORIZONTAL,
                        ModifyStarsWidget("modifyMovieStars"), 0.5,
                        ModifyTagsWidget("modifyMovieTags"), 0.0
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
   man.on_any_event(global_key_help_hook)

   db = database.Database(dbfile)
   man["db"] = db
   man["id"] = inspectdir
   man["ad"] = archivedir
   man["bd"] = bufferdir

   man.start()

