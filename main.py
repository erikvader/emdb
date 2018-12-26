#!/bin/python

import interface
import database

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
      self.value = "ESC: quit"

   def draw(self, win):
      if self.resized:
         win.erase()
      win.addstr(0, 0, self.value)

class ModifyWidget(interface.Widget):
   def __init__(self, name):
      super().__init__(name)
      self.value = "modify stuff here plz"

   def draw(self, win):
      if self.resized:
         win.erase()
      win.addstr(0, 0, self.value)

class GlobalBindings(interface.WrapperLayout):
   def key_event(self, key):
      if key == interface.ca.ESC:
         self.manager.stop()
      elif key == interface.ca.TAB:
         self.manager.get_widget("modifyMoviePopup").toggle()

class SelectorWidget(interface.FancyListWidget):
   def init(self):
      self.set_list(["hej{}".format(i)*5 + "a" for i in range(0, 100)])
      self.filter_by([i for i in range(0, len(self.get_indexlist())) if i % 2 == 0])

   def key_event(self, key):
      if key == interface.curses.KEY_DOWN or key == ord('j'):
         self.next()
      elif key == interface.curses.KEY_UP or key == ord('k'):
         self.prev()
      else:
         return False
      self.manager.get_widget("img").touch()
      return True

class PreviewWidget(interface.ImageWidget):
   def init(self):
      self.set_image("/home/erik/Pictures/PFUDOR_2.jpg")

def main():
   l = GlobalBindings(
      "globals",
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
               ModifyWidget("modifyMovie")
            ),
            maxh=10,
            maxw=50
         )
      )
   )

   man = interface.Manager(l)
   man.add_color(1, interface.curses.COLOR_RED, -1)
   man.start()

if __name__ == "__main__":
   main()
