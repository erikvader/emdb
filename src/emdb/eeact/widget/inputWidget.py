import curses
import curses.ascii as ca
from ..StringFormatter import ice
from .widget import Widget

class InputWidget(Widget):
   def __init__(self, name):
      super().__init__(name)
      self.value = []
      self.cursor = 0
      self._offset = 0

   def clear(self):
      self.value = []
      self.cursor = 0
      self._offset = 0

   def get_input(self):
      return "".join(self.value)

   def set_initial_input(self, initial):
      self.value = list(initial)
      self.cursor = min(len(self.value), self.w - 1)
      self._offset = len(self.value) - self.cursor

   def _fix_single_move(self):
      if self.cursor >= self.w:
         self.cursor -= 1
         self._offset += 1
      elif self.cursor < 0:
         self.cursor += 1
         self._offset -= 1

   def _shift_cursor_to_middle(self):
      m = self.w // 2
      to_move = m - self.cursor
      if to_move < 0:
         raise Exception("wrong side of the middle, implement later")
      to_move = min(to_move, self._offset)
      self._offset -= to_move
      self.cursor += to_move

   def key_event(self, key):
      if ca.isprint(key):
         self.value.insert(self._offset + self.cursor, chr(key))
         self.cursor += 1
         self._fix_single_move()
         self.changed()
      elif key == curses.KEY_LEFT:
         if self.cursor + self._offset > 0:
            self.cursor -= 1
            self._fix_single_move()
      elif key == curses.KEY_RIGHT:
         if self.cursor + self._offset < len(self.value):
            self.cursor += 1
            self._fix_single_move()
      elif key == ca.BS or key == curses.KEY_BACKSPACE:
         if self.cursor + self._offset > 0:
            del self.value[self._offset + self.cursor-1]
            self.cursor -= 1
            if self.cursor == 0:
               self._shift_cursor_to_middle()
            self.changed()
      else:
         return False
      self.touch()
      return True

   def changed(self):
      pass

   def draw(self, win):
      win.erase()
      x = 0
      for c in self.value[self._offset:]:
         if x > self.w:
            break
         ice(win.addch, 0, x, c)
         x += 1
      ice(win.chgat, 0, self.cursor, 1, self.manager.get_attr("input_cursor"))
