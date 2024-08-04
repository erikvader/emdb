from .layout import Layout

class WrapperLayout(Layout):
   def __init__(self, name, widget):
      super().__init__(name)
      self.widgets.append(widget)

   #pylint: disable=protected-access
   def _init(self, x, y, w, h, manager, parent):
      super()._init(x, y, w, h, manager, parent)
      self.widgets[0]._init(x, y, w, h, manager, self)

   def _resize(self, stdx, stdy, stdw, stdh):
      super()._resize(stdx, stdy, stdw, stdh)
      self.widgets[0]._resize(stdx, stdy, stdw, stdh)
