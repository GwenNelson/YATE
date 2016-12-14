import eventlet
eventlet.monkey_patch()
import curses
import curses.panel
import time

from yate import yatelog

from yate import yateclient

from yate import yateproto

from yate.yateproto import *


# see init_color_pairs() below
TOPSTATUS         = 1
TOPSTATUS_ONLINE  = 2
TOPSTATUS_OFFLINE = 3
TOPSTATUS_FG = curses.COLOR_WHITE
TOPSTATUS_BG = curses.COLOR_BLUE

VOXEL_COLOR_PAIR = 4

voxel_colors = {YATE_VOXEL_EMPTY:              curses.COLOR_BLACK,
                YATE_VOXEL_TOTAL_OBSTACLE:     curses.COLOR_RED,
                YATE_VOXEL_EASY_OBSTACLE:      curses.COLOR_GREEN,
                YATE_VOXEL_DOOR_OBSTACLE:      curses.COLOR_YELLOW,
                YATE_VOXEL_DOOR_EASY_DESTROY:  curses.COLOR_YELLOW,
                YATE_VOXEL_DOOR_HARD_DESTROY:  curses.COLOR_YELLOW,
                YATE_VOXEL_HARD_OBSTACLE:      curses.COLOR_RED,
                YATE_VOXEL_UNKNOWN:            curses.COLOR_BLACK}

voxel_static      = ' '
voxel_destroyable = '#'
voxel_unknown     = '?'

voxel_chars = {YATE_VOXEL_EMPTY:              voxel_static,
               YATE_VOXEL_TOTAL_OBSTACLE:     voxel_static,
               YATE_VOXEL_EASY_OBSTACLE:      voxel_destroyable,
               YATE_VOXEL_DOOR_OBSTACLE:      voxel_static,
               YATE_VOXEL_DOOR_EASY_DESTROY:  voxel_destroyable,
               YATE_VOXEL_DOOR_HARD_DESTROY:  voxel_destroyable,
               YATE_VOXEL_HARD_OBSTACLE:      voxel_destroyable,
               YATE_VOXEL_UNKNOWN:            voxel_unknown}

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
       self.av_pos = (0,0,0)

       self.init_log()
       self.init_voxel_display()
       self.percept_delay = 0

       self.disp_func = self.log_display
       self.client    = yateclient.YATEClient(connect_cb = self.connect_cb, voxel_update_cb=self.voxel_update_cb,avatar_pos_cb=self.avatar_pos_cb)
       self.running = True
       yatelog.info('yate_console','Starting up')
       self.draw_scr()
       self.pool = eventlet.GreenPool(100)
       self.pool.spawn(self.main_ui_loop)
       while self.running: eventlet.greenthread.sleep(1)
       curses.curs_set(1)

   def init_color_pairs(self):
       curses.init_pair(TOPSTATUS,TOPSTATUS_FG,TOPSTATUS_BG)
       curses.init_pair(TOPSTATUS_ONLINE,curses.COLOR_GREEN,TOPSTATUS_BG)
       curses.init_pair(TOPSTATUS_OFFLINE,curses.COLOR_RED,TOPSTATUS_BG)
       # create some color pairs for voxel types in a hacky way
       for item in dir(yateproto):
           if item.startswith('YATE_VOXEL_'):
              curses.init_pair(VOXEL_COLOR_PAIR + getattr(yateproto,item), curses.COLOR_WHITE,voxel_colors[getattr(yateproto,item)])

   def init_log(self):
       self.log_win   = self.scr.subwin(self.h-4,self.w-2,self.y+3,self.x+1)
       self.log_win.move(1,0)
       self.log_win.scrollok(True)
       self.log_panel = curses.panel.new_panel(self.log_win)
       self.logger    = yatelog.get_curses_logger(self.log_win)

   def voxel_update_cb(self,voxel):
       """ If a voxel is updated within the visual range and on the same level as the avatar, update the display
       """
       vox_pos           = voxel.get_pos()
       voxmap            = self.client.get_map()
       if not voxmap.is_visible(vox_pos): return

       avatar_pos        = voxmap.get_avatar_pos()
       av_x,av_y,av_z    = avatar_pos
       vox_x,vox_y,vox_z = vox_pos


       if round(vox_z) != round(av_z): return

       if vox_pos == avatar_pos:
          vox_char = 'A'
       else:
          vox_char = voxel_chars[voxel.get_basic_type()]
       self.voxel_win.addstr(vox_y+4,vox_x+4,vox_char,curses.color_pair(VOXEL_COLOR_PAIR+voxel.get_basic_type()))
   def avatar_pos_cb(self,spatial_position):
       if self.av_pos != (0,0,0):
          if self.av_pos != spatial_position:
             self.client.refresh_vis(voxel_pos=self.av_pos)
          self.av_pos = tuple(spatial_position)
       av_x,av_y,av_z = spatial_position
       self.voxel_win.addstr(av_y+4,av_x+4,'A')
       self.av_pos = spatial_position
       
   def init_voxel_display(self):
       self.voxel_win   = curses.newwin(self.h-4,self.w-2,self.y+3,self.x+2)

       self.voxel_panel = curses.panel.new_panel(self.voxel_win)
       self.voxel_panel.bottom()
       self.voxel_panel.hide()
       for x in xrange(1,self.w-3,1):
           for y in xrange(1,self.h-4):
               eventlet.greenthread.sleep(0)
               self.voxel_win.addstr(y,x,'!',curses.color_pair(VOXEL_COLOR_PAIR+yateproto.YATE_VOXEL_UNKNOWN))

   def do_move(self,key):
       # for now this is quite silly and only works with the mock driver
       if key=='w': vector = ( 0,-1,0)
       if key=='a': vector = ( 0, 1,0)
       if key=='s': vector = (-1, 0,0)
       if key=='d': vector = ( 1, 0,0)
       self.client.move_vector(vector)

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
             if self.client.is_connected():
                if inkey == 'v':
                   self.disp_func = self.voxel_display
                   self.draw_scr()
                if not (inkey is None):
                   if inkey in 'wasd':
                      self.do_move(inkey)
             if inkey == 'l':
                self.disp_func = self.log_display
                self.draw_scr()
          except Exception,e:
             yatelog.minor_exception('yate_console','')
          try:
             self.draw_scr()
          except Exception,e:
             pass
   def track_dirty_thread(self):
       while self.client.is_connected():
          eventlet.greenthread.sleep(self.percept_delay)
          if self.client.envmap.is_complete():
             self.percept_delay = 1.5
          else:
             self.percept_delay = 0
   def perception_thread(self):
       yatelog.info('yate_console','Perception thread running')
       self.client.mark_dirty()
       while self.client.is_connected():
          try:
             self.client.refresh_vis()
          except:
             yatelog.minor_exception('yate_console','failed during visual update')
          eventlet.greenthread.sleep(self.percept_delay)
   def connect_cb(self):
       self.pool.spawn(self.track_dirty_thread)
       self.pool.spawn(self.perception_thread)
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
   def voxel_display(self):
       self.voxel_panel.top()
       self.voxel_panel.show()
       self.voxel_win.box()
       self.voxel_win.refresh()
       curses.panel.update_panels()
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
          self.scr.addstr(self.y+2,self.x+2,'[Q quit] [V voxel view] [L log view] [H health view] [I inventory view] [/ enter command] [wasd manual move]',curses.color_pair(TOPSTATUS))
       else:
          self.scr.addstr(self.y+1,self.x+21,'Offline',curses.color_pair(TOPSTATUS_OFFLINE)|curses.A_BOLD)
          self.scr.addstr(self.y+2,self.x+2,'Press C to connect and Q to quit',curses.color_pair(TOPSTATUS))
   def draw_scr(self):
       self.scr.border()
       self.draw_status()
       self.disp_func()
       self.scr.refresh()

curses.wrapper(YATEConsoleApp)
