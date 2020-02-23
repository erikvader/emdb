from ..widget.widget import Widget

class Layout(Widget):
   def __init__(self, name):
      super().__init__(name)
      self.widgets = []
      self.focused = 0
      self.is_layout = True
      self.focusable = False

   #pylint: disable=protected-access
   def _covered(self, covered):
      super()._covered(covered)
      for w in self.widgets:
         w._covered(covered)

   #pylint: disable=protected-access
   def _show(self):
      for w in self.widgets:
         w._show()

   #pylint: disable=protected-access
   def _hide(self):
      for w in self.widgets:
         w._hide()

   #pylint: disable=protected-access
   def is_hidden(self):
      for w in self.widgets:
         if not w.is_hidden():
            return False
      return True

   #pylint: disable=protected-access
   def _focus_child(self, child):
      super()._focus_child(child)
      for i,w in enumerate(self.widgets):
         if w == child:
            self.change_focus(i, dofocus=False)
            break
      else:
         raise Exception("didn't find any child to focus")

      if self.parent:
         self.parent._focus_child(self)

   def _unfocus(self):
      self.widgets[self.focused]._unfocus()

   def _focus(self):
      self.widgets[self.focused]._focus()

   def change_focus(self, to, dofocus=True):
      newfocus = to % len(self.widgets)
      if newfocus != self.focused:
         self.widgets[self.focused]._unfocus()
         self.focused = newfocus
         if dofocus:
            self.widgets[self.focused]._focus()

   # pylint: disable=protected-access
   def _key_event(self, key):
      if not self.widgets[self.focused]._key_event(key):
         return self.key_event(key)
      return True

   #pylint: disable=protected-access
   def _draw(self):
      self.redraw = True
      self.resized = False
      for w in self.widgets:
         if w.redraw:
            w._draw()
