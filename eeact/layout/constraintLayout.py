from .layout import Layout

class ConstraintLayout(Layout):
   def __init__(self, widget, maxw=None, maxh=None):
      super().__init__("constraint_{}".format(widget.name))
      self.widgets.append(widget)
      self.maxw = maxw
      self.maxh = maxh

   def _get_size(self):
      pw = min(self.w, self.maxw) if self.maxw else self.w
      ph = min(self.h, self.maxh) if self.maxh else self.h
      px = self.x + int((self.w - pw) / 2)
      py = self.y + int((self.h - ph) / 2)
      return (px, py, pw, ph)

   #pylint: disable=protected-access
   def _init(self, x, y, w, h, manager, parent):
      super()._init(x, y, w, h, manager, parent)
      self.widgets[0]._init(*self._get_size(), manager, self)

   def _resize(self, stdx, stdy, stdw, stdh):
      super()._resize(stdx, stdy, stdw, stdh)
      self.widgets[0]._resize(*self._get_size())
