import curses.ascii as ca
from .popupLayout import PopupLayout
from ...widget.widget import Widget
from ..borderWrapperLayout import BorderWrapperLayout
from ..constraintLayout import ConstraintLayout
import asyncio

class InfoPopup(PopupLayout):
   INFO = 1
   WARNING = 2
   ERROR = 3

   YESNO = 1
   OKESC = 2
   BLOCK = 3

   class InfoWidget(Widget):
      def __init__(self, name):
         super().__init__(name)
         self.msg = ""
         self.severity = InfoPopup.INFO
         self.kind = InfoPopup.BLOCK
         self.fut = None

      def set_yesno(self, msg):
         self.msg = msg
         self.kind = InfoPopup.YESNO
         self.touch()
         self.fut = asyncio.get_running_loop().create_future()
         return self.fut

      def set_ok(self, msg, severity):
         self.msg = msg
         self.severity = severity
         self.kind = InfoPopup.OKESC
         self.touch()
         self.fut = asyncio.get_running_loop().create_future()
         return self.fut

      def set_block(self, msg):
         self.msg = msg
         self.kind = InfoPopup.BLOCK
         self.touch()

      def _get_severity_text(self):
         if self.severity == InfoPopup.INFO:
            return "${info_info}Info$0"
         elif self.severity == InfoPopup.WARNING:
            return "${info_warning}Warning$0"
         elif self.severity == InfoPopup.ERROR:
            return "${info_error}Error$0"

      def draw(self, win):
         win.erase()
         if self.kind == InfoPopup.OKESC:
            self.format_draw(win, 0, 0, self._get_severity_text())
            mid = (self.h-1) // 2
         elif self.kind == InfoPopup.YESNO:
            mid = self.h // 2
         elif self.kind == InfoPopup.BLOCK:
            self.format_draw(win, 0, 0, "${info_block}Blocked$0")
            mid = (self.h-1) // 2
         self.format_draw(win, 0, mid, self.msg, centered=True)

      def key_event(self, key):
         if self.kind == InfoPopup.YESNO:
            if key == ord('y'):
               self.fut.set_result(True)
            elif key == ord('n'):
               self.fut.set_result(False)
         elif self.kind == InfoPopup.OKESC:
            if key == ord('y') or key == ca.NL:
               self.fut.set_result(True)
         elif self.kind == InfoPopup.BLOCK:
            pass
         return True

   def __init__(self, name, base, popmaxw, popmaxh):
      self.infoWidget = self.InfoWidget("{}_InfoWidget".format(name))
      super().__init__(
         name,
         base,
         ConstraintLayout(
            BorderWrapperLayout("rltb", self.infoWidget),
            maxw=popmaxw,
            maxh=popmaxh
         )
      )

   def show_info(self, msg, severity=INFO):
      fut = self.infoWidget.set_ok(
         msg,
         severity
      )
      self.show_popup()
      return fut

   def show_question(self, msg):
      fut = self.infoWidget.set_yesno(msg)
      self.show_popup()
      return fut

   def show_blocked(self, msg):
      self.infoWidget.set_block(msg)
      self.show_popup()
