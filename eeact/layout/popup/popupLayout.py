from ..layout import Layout

class PopupLayout(Layout):
   def __init__(self, name, base, popup):
      super().__init__(name)
      self.widgets = [base, popup]
      self.popupped = False

   #pylint: disable=protected-access
   def _init(self, x, y, w, h, manager, parent):
      super()._init(x, y, w, h, manager, parent)
      self.widgets[0]._init(x, y, w, h, manager, self)
      self.widgets[1]._init(x, y, w, h, manager, self)
      self.hide_popup()

   def show_popup(self):
      self.popupped = True
      self.widgets[1]._show()
      # self.widgets[1]._top()
      self.widgets[0]._covered(True)
      self.widgets[1].touch()
      self.change_focus(1)

   def hide_popup(self):
      self.popupped = False
      self.widgets[1]._hide()
      self.widgets[0]._covered(False)
      self.change_focus(0)

   def is_popupped(self):
      return self.popupped

   def toggle(self):
      if not self.is_popupped():
         self.show_popup()
      else:
         self.hide_popup()

   #pylint: disable=protected-access,fixme
   def _resize(self, stdx, stdy, stdw, stdh):
      # FIXME: self.resize is called before the children are updated, might be a problem
      super()._resize(stdx, stdy, stdw, stdh)
      self.widgets[0]._resize(stdx, stdy, stdw, stdh)
      self.widgets[1]._resize(stdx, stdy, stdw, stdh)

   #pylint: disable=protected-access
   def _focus_child(self, child):
      super()._focus_child(child)
      if self.focused == 1:
         self.show_popup()
      else:
         self.hide_popup()

   def _covered(self, covered):
      if not self.is_popupped():
         super()._covered(covered)
