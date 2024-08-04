import curses
import curses.panel as cp
from .. import StringFormatter

class Widget():
   def __init__(self, name):
      self.x = 0
      self.y = 0
      self.w = 0
      self.h = 0
      self.redraw = True
      self.is_focused = False
      self.panel = None
      self.is_layout = False
      self.resized = False
      self.parent = None
      self.manager = None
      self.name = name
      self.focusable = True
      self.initialized = False

   def _init(self, x, y, w, h, manager, parent):
      self.x = x
      self.y = y
      self.w = w
      self.h = h
      if not self.is_layout:
         self.panel = cp.new_panel(curses.newwin(self.h, self.w, self.y, self.x))
      else:
         self.panel = None
      self.parent = parent
      self.manager = manager
      self.manager.widgets[self.name] = self
      self.init()
      self.initialized = True

   def init(self):
      pass

   def _draw(self):
      self.draw(self.panel.window())
      self.redraw = False
      self.resized = False

   def draw(self, win):
      pass

   def format_draw(self, win, x, y, string, **kwargs):
      return StringFormatter.draw(win, x, y, string, self.manager, **kwargs)

   def _key_event(self, key):
      return self.key_event(key)

   def key_event(self, _key):
      return False

   def touch(self):
      self.redraw = True

   def untouch(self):
      self.redraw = False

   def _resize(self, stdx, stdy, stdw, stdh):
      if self.panel:
         self.panel.window().resize(stdh, stdw)
         self.panel.move(stdy, stdx)

      self.x = stdx
      self.y = stdy
      self.w = stdw
      self.h = stdh

      self.touch()
      self.resized = True
      self.resize(stdx, stdy, stdw, stdh)

   def resize(self, stdx, stdy, stdw, stdh):
      pass

   def _covered(self, covered):
      pass

   #pylint: disable=protected-access
   def focus(self):
      if not self.focusable:
         raise Exception("can't focus anything non-focusable")

      self._focus()
      if self.parent:
         self.parent._focus_child(self)

   def onfocus(self):
      pass

   def _focus_child(self, _child):
      if not self.is_layout:
         raise Exception("can't focus child on a widget")

   def _unfocus(self):
      self.is_focused = False
      self.touch()

   def _focus(self):
      self.is_focused = True
      self.manager.current_focus = self
      self.touch()
      self.onfocus()

   def _hide(self):
      if self.panel:
         self.panel.hide()

   def _show(self):
      if self.panel:
         self.panel.show()

   def is_hidden(self):
      if self.panel:
         return self.panel.hidden()
      raise Exception("this widget doesn't have a panel")

   def map_focused(self, f, *args, **kwargs):
      if kwargs["top_down"]:
         if self.parent:
            self.parent.map_focused(f, *args, **kwargs)
         f(self, *args, **kwargs)
      else:
         f(self, *args, **kwargs)
         if self.parent:
            self.parent.map_focused(f, *args, **kwargs)
