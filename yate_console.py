import eventlet
eventlet.monkey_patch()
import curses
import time

TOPSTATUS         = 1
TOPSTATUS_ONLINE  = 2
TOPSTATUS_OFFLINE = 3
TOPSTATUS_FG = curses.COLOR_WHITE
TOPSTATUS_BG = curses.COLOR_BLUE

class YATEConsoleApp:
   def __init__(self,scr):
       self.scr = scr
       curses.curs_set(0)
       curses.halfdelay(1)
       self.init_color_pairs()
       curses.init_pair(TOPSTATUS,TOPSTATUS_FG,TOPSTATUS_BG)
       self.running   = False
       self.connected = False
       self.y,self.x = self.scr.getbegyx()
       self.h,self.w = self.scr.getmaxyx()


       self.disp_func = self.default_disp
       self.running = True
       self.draw_scr()
       self.main_ui_loop()

       curses.curs_set(1)

   def init_color_pairs(self):
       curses.init_pair(TOPSTATUS,TOPSTATUS_FG,TOPSTATUS_BG)
       curses.init_pair(TOPSTATUS_ONLINE,curses.COLOR_GREEN,TOPSTATUS_BG)
       curses.init_pair(TOPSTATUS_OFFLINE,curses.COLOR_RED,TOPSTATUS_BG)
   def main_ui_loop(self):
       while self.running:
          inkey = None
          try:
             inkey = self.scr.getkey()
             if inkey == 'c': self.connect()
          except Exception,e:
             pass
          try:
             self.draw_scr()
          except Exception,e:
             pass
   def connect(self):
       self.scr.addstr(self.y+2,self.x+1,' '*(self.w-2),curses.color_pair(TOPSTATUS))
       self.scr.addstr(self.y+2,self.x+1,' Enter port number on localhost: ',curses.color_pair(TOPSTATUS))
       self.scr.refresh()
       curses.curs_set(1)
       curses.echo()
       self.scr.attron(curses.color_pair(TOPSTATUS))
       port_str = self.scr.getstr(self.y+2,self.x+34,8)
       self.scr.addstr(self.y+2,self.x+34,str(port_str),curses.color_pair(TOPSTATUS))
       self.scr.attroff(curses.color_pair(TOPSTATUS))
       self.scr.refresh()
       curses.noecho()
       curses.curs_set(0)
   def default_disp(self):
       pass
   def draw_status(self):
       self.scr.addstr(self.y+1,self.x+1,' '*(self.w-2),curses.color_pair(TOPSTATUS))
       self.scr.addstr(self.y+2,self.x+1,' '*(self.w-2),curses.color_pair(TOPSTATUS))
       self.scr.addstr(self.y+1,self.x+2,'Connection status: ',curses.color_pair(TOPSTATUS))
       if self.connected:
          self.scr.addstr(self.y+1,self.x+21,'Online ',curses.color_pair(TOPSTATUS_ONLINE)|curses.A_BOLD)
          self.scr.addstr(self.y+2,self.x+2,'Press D to disconnect',curses.color_pair(TOPSTATUS))
       else:
          self.scr.addstr(self.y+1,self.x+21,'Offline',curses.color_pair(TOPSTATUS_OFFLINE)|curses.A_BOLD)
          self.scr.addstr(self.y+2,self.x+2,'Press C to connect',curses.color_pair(TOPSTATUS))
   def draw_scr(self):
       self.scr.border()
       self.draw_status()
       self.disp_func()
       self.scr.refresh()

curses.wrapper(YATEConsoleApp)
