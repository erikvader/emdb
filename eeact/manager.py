import curses
import curses.panel as cp
import os
from time import monotonic_ns
from threading import Thread, Lock
from collections import deque
import ueberzug.lib.v0 as ueberzug

# pylint: disable=protected-access
class Manager():
   def __init__(self, layout):
      self.running = True
      self.attr_names = {"0": 0}
      self.attr_override = []
      self.layout = layout
      self.widgets = {}
      self.global_hook = []
      self.current_focus = None
      self.global_vars = {}
      self.stdscr = None
      self.event_queue = deque()
      self.event_lock = Lock()
      self.bg_jobs = []
      self.curses_blocking = True
      self.idle_jobs = []

   def __getitem__(self, key):
      return self.global_vars[key]

   def __setitem__(self, key, value):
      self.global_vars[key] = value

   def __delitem__(self, key):
      del self.global_vars[key]

   def __enter__(self):
      os.environ.setdefault('ESCDELAY', '0')
      self.stdscr = curses.initscr()
      curses.noecho()
      curses.cbreak()
      self.stdscr.keypad(True)
      try:
         curses.start_color()
         curses.use_default_colors()
      except:
         pass
      return self

   def __exit__(self, _exc_type, _exc_value, _traceback):
      if self.stdscr:
         self.stdscr.keypad(0)
         curses.echo()
         curses.nocbreak()
         curses.endwin()
      return False

   def on_any_event(self, f):
      self.global_hook.append(f)

   def get_widget(self, name):
      if name not in self.widgets:
         raise Exception("can't find widget with name {}".format(name))
      return self.widgets[name]

   def init_color(self, index, fg, bg):
      curses.init_pair(index, fg, bg)

   def add_color(self, name, index):
      self.add_attr(name, curses.color_pair(index))

   def add_attr(self, name, attr):
      self.attr_names[name] = attr

   def get_attr(self, name):
      for o in reversed(self.attr_override):
         if name == o[0]:
            return o[1]
      return self.attr_names.get(name, 0)

   def push_attr_override(self, name, attr):
      self.attr_override.append((name, attr))

   def pop_attr_override(self):
      if not self.attr_override:
         raise Exception("override stack is empty")
      self.attr_override.pop()

   def map_focused(self, f, *args, top_down=True, **kwargs):
      self.current_focus.map_focused(f, *args, top_down=top_down, **kwargs)

   def get_focused(self):
      return self.current_focus

   def start_bg_job(self, f, *args):
      fixed_args = (self.event_lock, self.event_queue)
      t = Thread(daemon=True, target=f, args=(*fixed_args, *args))
      t.start()
      self.bg_jobs.append(t)

   def start_idle_job(self, f, *args):
      self.idle_jobs.append(f)

   def start(self):
      self._main_fun(self.stdscr)

   def stop(self):
      self.running = False

   def _main_fun(self, stdscr):
      curses.curs_set(False)
      stdscr.immedok(False)

      maxy, maxx = stdscr.getmaxyx()
      self.layout._init(0, 0, maxx, maxy, self, None)

      self.get_widget("MAIN").focus()

      while self.running:

         for f in self.global_hook:
            f(self)

         self.layout._draw()

         curses.update_lines_cols()
         cp.update_panels()
         curses.doupdate()

         self._get_event(stdscr)

   def _get_event(self, stdscr):
      start = monotonic_ns()
      while True:
         self.bg_jobs = [j for j in self.bg_jobs if j.is_alive()]
         with self.event_lock:
            update = False
            while self.event_queue:
               update |= self.event_queue.popleft()(self)

            if update:
               break

         if self.idle_jobs and monotonic_ns() - start > 40*1000000:
            update = False
            while self.idle_jobs:
               update |= self.idle_jobs.pop()(self)

            if update:
               break

         if not self.bg_jobs and not self.idle_jobs:
            if not self.curses_blocking:
               stdscr.timeout(-1)
               self.curses_blocking = True
         else:
            if self.curses_blocking:
               stdscr.timeout(50)
               self.curses_blocking = False

         k = stdscr.getch()
         if k == -1:
            continue
         elif k == curses.KEY_RESIZE:
            maxy, maxx = stdscr.getmaxyx()
            self.layout._resize(0, 0, maxx, maxy)
            break
         else:
            if self.layout._key_event(k):
               break
