from .layout import Layout

class TabbedLayout(Layout):
   def __init__(self, name, *widgets):
      super().__init__(name)
      self.widgets = widgets

   #pylint: disable=protected-access
   def _init(self, x, y, w, h, manager, parent):
      super()._init(x, y, w, h, manager, parent)
      for wi in self.widgets:
         wi._init(x, y, w, h, manager, self)

      for wi in self.widgets[1:]:
         wi._hide()

   def _tab_to(self, index):
      self.widgets[self.focused]._hide()
      self.change_focus(index)
      self.widgets[self.focused]._show()
      self.widgets[self.focused].touch()

   def show_next(self):
      self._tab_to(self.focused + 1)

   def show_prev(self):
      self._tab_to(self.focused - 1)

   #pylint: disable=protected-access,fixme
   def _resize(self, stdx, stdy, stdw, stdh):
      # FIXME: self.resize is called before the children are updated, might be a problem
      super()._resize(stdx, stdy, stdw, stdh)
      for w in self.widgets:
         w._resize(stdx, stdy, stdw, stdh)

   #pylint: disable=protected-access
   def _focus_child(self, child):
      oldfocus = self.focused
      super()._focus_child(child)
      if self.focused != oldfocus:
         self.widgets[oldfocus]._hide()
         self.widgets[self.focused]._show()
         # self.widgets[self.focused].touch()
