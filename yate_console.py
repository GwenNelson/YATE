import eventlet
eventlet.monkey_patch()
import curses
import curses.panel
import time

from yate import yatelog

from yate import yateclient

TOPSTATUS         = 1
TOPSTATUS_ONLINE  = 2
TOPSTATUS_OFFLINE = 3
TOPSTATUS_FG = curses.COLOR_WHITE
TOPSTATUS_BG = curses.COLOR_BLUE

class YATEConsoleApp:
   def __init__(self,scr):
       self.scr = scr
       curses.curs_set(0)
       self.init_color_pairs()
       curses.init_pair(TOPSTATUS,TOPSTATUS_FG,TOPSTATUS_BG)
       self.scr.nodelay(1)
       self.running   = False
       self.y,self.x = self.scr.getbegyx()
       self.h,self.w = self.scr.getmaxyx()

       self.log_win   = self.scr.subwin(self.h-4,self.w-2,self.y+3,self.x+1)
       self.log_win.move(1,0)
       self.log_win.scrollok(True)
       self.log_panel = curses.panel.new_panel(self.log_win)
       self.logger    = yatelog.get_curses_logger(self.log_win)
       self.disp_func = self.log_display
       self.client    = yateclient.YATEClient(connect_cb = self.connect_cb)
       self.running = True
       yatelog.info('yate_console','Starting up')
       self.draw_scr()
       self.pool = eventlet.GreenPool(100)
       self.main_ui_loop()

       curses.curs_set(1)

   def init_color_pairs(self):
       curses.init_pair(TOPSTATUS,TOPSTATUS_FG,TOPSTATUS_BG)
       curses.init_pair(TOPSTATUS_ONLINE,curses.COLOR_GREEN,TOPSTATUS_BG)
       curses.init_pair(TOPSTATUS_OFFLINE,curses.COLOR_RED,TOPSTATUS_BG)
   def main_ui_loop(self):
       while self.running:
          eventlet.greenthread.sleep(0)
          self.draw_scr()
          inkey = None
          try:
             inkey = self.scr.getkey()
          except:
             pass
          try:
             if inkey == 'c': self.connect()
             if inkey == 'q': self.running = False
          except Exception,e:
             yatelog.minor_exception('yate_console','')
          try:
             self.draw_scr()
          except Exception,e:
             pass
   def perception_thread(self):
       yatelog.info('yate_console','Perception thread running')
       while self.client.is_connected():
          self.client.send_request_visual()
          eventlet.greenthread.sleep(5)
   def connect_cb(self):
       self.pool.spawn_n(self.perception_thread)
   def connect(self):
       self.scr.nodelay(0)
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
       self.scr.nodelay(1)
       self.client.connect_to(('127.0.0.1',int(port_str)))
   def log_display(self):
       self.log_panel.top()
       self.log_panel.show()
       self.log_win.box()
       curses.panel.update_panels()
   def draw_status(self):
       self.scr.addstr(self.y+1,self.x+1,' '*(self.w-2),curses.color_pair(TOPSTATUS))
       self.scr.addstr(self.y+2,self.x+1,' '*(self.w-2),curses.color_pair(TOPSTATUS))
       self.scr.addstr(self.y+1,self.x+2,'Connection status: ',curses.color_pair(TOPSTATUS))
       if self.client.is_connected():
          self.scr.addstr(self.y+1,self.x+21,'Online ',curses.color_pair(TOPSTATUS_ONLINE)|curses.A_BOLD)
          self.scr.addstr(self.y+2,self.x+2,'[Q quit] [V voxel view] [L log view] [H health view] [I inventory view] [/ enter command]',curses.color_pair(TOPSTATUS))
       else:
          self.scr.addstr(self.y+1,self.x+21,'Offline',curses.color_pair(TOPSTATUS_OFFLINE)|curses.A_BOLD)
          self.scr.addstr(self.y+2,self.x+2,'Press C to connect and Q to quit',curses.color_pair(TOPSTATUS))
   def draw_scr(self):
       self.scr.border()
       self.draw_status()
       self.disp_func()
       self.scr.refresh()

curses.wrapper(YATEConsoleApp)
