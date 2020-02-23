import curses
import curses.panel as cp
import ueberzug.lib.v0 as ueberzug
import asyncio

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
      self.ueber = None
      self.refresh_event = None
      self.startup_jobs = []

   def __getitem__(self, key):
      return self.global_vars[key]

   def __setitem__(self, key, value):
      self.global_vars[key] = value

   def __delitem__(self, key):
      del self.global_vars[key]

   def on_any_event(self, f):
      self.global_hook.append(f)

   def get_widget(self, name):
      if name not in self.widgets:
         raise Exception("can't find widget with name {}".format(name))
      return self.widgets[name]

   def init_color(self, index, fg, bg):
      self.startup_jobs.append(lambda: curses.init_pair(index, fg, bg))

   def add_color(self, name, index):
      self.startup_jobs.append(lambda: self.add_attr(name, curses.color_pair(index)))

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

   def start(self, ueber=False):
      def ueber_wrapper(f):
         if ueber:
            with ueberzug.Canvas() as canvas:
               self.ueber = canvas
               f()
         else:
            f()

      ueber_wrapper(
         lambda: curses.wrapper(lambda stdscr: asyncio.run(self._main_fun(stdscr)))
      )

   def stop(self):
      self.running = False

   async def _main_fun(self, stdscr):
      curses.curs_set(False)
      stdscr.immedok(False)
      curses.use_default_colors()
      stdscr.timeout(100)

      for f in self.startup_jobs:
         f()
      self.startup_jobs.clear()

      self.refresh_event = asyncio.Event()
      loop = asyncio.get_running_loop()
      loop.call_soon(self._read_keys, stdscr, loop)

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

         await self.refresh_event.wait()
         self.refresh_event.clear()

   def _read_keys(self, stdscr, loop):
      # loop = asyncio.get_running_loop()
      # NOTE: resize funkade inte pga signals o threads
      # https://stackoverflow.com/questions/53822353/where-does-curses-inject-key-resize-on-endwin-and-refresh
      # k = await loop.run_in_executor(None, stdscr.getch)

      if not self.running:
         return

      k = stdscr.getch()
      if k == -1:
         pass
      elif k == curses.KEY_RESIZE:
         maxy, maxx = stdscr.getmaxyx()
         self.layout._resize(0, 0, maxx, maxy)
         self.refresh_event.set()
      else:
         if self.layout._key_event(k):
            self.refresh_event.set()

      loop.call_soon(self._read_keys, stdscr, loop)
