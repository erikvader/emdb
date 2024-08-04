import curses
from ..StringFormatter import ice
from .layout import Layout

class BorderWrapperLayout(Layout):
   def __init__(self, edges, widget):
      super().__init__("border_{}".format(widget.name))
      self.widgets.append(widget)
      self.edges = edges

   def _show(self):
      self.panel.show()
      super()._show()

   def _hide(self):
      self.panel.hide()
      super()._hide()

   def _get_child_size(self):
      x = self.x
      y = self.y
      w = self.w
      h = self.h
      if 'l' in self.edges:
         x += 1
         w -= 1
      if 'r' in self.edges:
         w -= 1
      if 't' in self.edges:
         y += 1
         h -= 1
      if 'b' in self.edges:
         h -= 1
      return x, y, w, h

   #pylint: disable=protected-access
   def _init(self, x, y, w, h, manager, parent):
      self.is_layout = False
      super()._init(x, y, w, h, manager, parent)
      self.widgets[0]._init(*self._get_child_size(), manager, self)
      self.is_layout = True
      self.resized = True

   def _resize(self, stdx, stdy, stdw, stdh):
      super()._resize(stdx, stdy, stdw, stdh)
      self.widgets[0]._resize(*self._get_child_size())

   def _draw(self):
      if self.resized:
         win = self.panel.window()
         win.erase()
         if 't' in self.edges:
            ice(win.hline, 0, 0, curses.ACS_HLINE, self.w)
         if 'b' in self.edges:
            ice(win.hline, self.h - 1, 0, curses.ACS_HLINE, self.w)
         if 'l' in self.edges:
            ice(win.vline, 0, 0, curses.ACS_VLINE, self.h)
         if 'r' in self.edges:
            ice(win.vline, 0, self.w - 1, curses.ACS_VLINE, self.h)
         if 'l' in self.edges and 't' in self.edges or '1' in self.edges:
            ice(win.addch, 0, 0, curses.ACS_ULCORNER)
         if 'l' in self.edges and 'b' in self.edges or '3' in self.edges:
            ice(win.addch, self.h - 1, 0, curses.ACS_LLCORNER)
         if 'r' in self.edges and 't' in self.edges or '2' in self.edges:
            ice(win.addch, 0, self.w - 1, curses.ACS_URCORNER)
         if 'r' in self.edges and 'b' in self.edges or '4' in self.edges:
            ice(win.addch, self.h - 1, self.w - 1, curses.ACS_LRCORNER)
      super()._draw()
