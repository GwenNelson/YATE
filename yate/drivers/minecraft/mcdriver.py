import eventlet
eventlet.monkey_patch()
import base
import yatelog
import time

from mcproto import mcsock
from mcproto import buffer

class MinecraftDriver(base.YateBaseDriver):
   def __init__(self,username=None,password=None,server='127.0.0.1:25565'):
       super(MinecraftDriver,self).__init__(username=username,password=password,server=server)
       self.username    = username
       self.password    = password
       self.avatar_uuid = None
       self.avatar_name = username # not always the same, just usually
       server_ip,server_port = server.split(':')
       self.server_addr = (server_ip,int(server_port))
       yatelog.info('minecraft','Minecraft driver starting up')
   
       pack_handlers = {'login_success':           self.handle_login_success,
                        'player_position_and_look':self.handle_player_position_and_look}

       self.sock = mcsock.MCSocket(self.server_addr,handlers=pack_handlers,display_name=username)
       self.sock.switch_mode(mcsock.protocol_modes['login'])
       self.tick_delay       = (1.0/20.0)
       self.last_tick        = time.time() - self.tick_delay # make sure that we tick after connecting
       self.last_full_update = time.time() - 1.0             # make sure we run a full update after connecting
       self.av_pos           = None # stores the avatar position, in minecraft format also known as (x,z,y) to sane humans
       self.av_pitch         = None
       self.av_yaw           = None
       self.on_ground        = True
   def minecraft_client_tick(self):
       """ This is called 20 times per second and does per-tick things
       """
       self.sock.send_player(buffer.Buffer.pack('?', True)) # send a Player packet every tick
   def handle_player_position_and_look(self,buff):
       """ When this packet comes in, it lets us know where we are
       """
       if self.av_pos is None: # this is a hack for the first update
          self.av_pos   = [0.0,0.0,0.0]
          self.av_pitch = 0.0
          self.av_yaw   = 0.0
       pos_look = buff.unpack('dddff')

       if self.sock.protocol_version <= 5: # 1.7.x - probably never gonna be used, but what the hell
          self.on_ground = buff.unpack('?')
          self.av_pos    = pos_look[0],pos_look[1],pos_look[2]
          self.av_yaw    = pos_look[3]
          self.av_pitch  = pos_look[4]
       else:
          flags = buff.unpack('B') # handle relative vs absolute in 1.8.x+
          for i in xrange(0,2):
              if flags & (1 << i):
                 self.av_pos[i] += pos_look[i]
              else:
                 self.av_pos[i]  = pos_look[i]
          if flags & (1 << 3): # check for absolute yaw - that'd be a cool band name: absolute yaw
             self.av_yaw += pos_look[3]
          else:
             self.av_yaw  = pos_look[3]
          if flags & (1 << 4): # check for absolute pitch - which would be a cool thing to have in the cool band
             self.av_pitch += pos_look[4] # most musicians do fine with relative pitch, i do when jamming on guitar
          else:
             self.av_pitch  = pos_look[4]
       if self.sock.protocol_version > 47: # 1.9.x+ sends teleports, so we need to confirm them
          teleport_id = buff.unpack_varint()
          self.sock.send_teleport_confirm(buffer.Buffer.pack_varint(teleport_id))

   def get_rot(self):
       """ We calculate this from the avatar pitch and yaw stuff
       """
       rot_x = self.av_yaw   % 360.0 # really notch, why on earth is this not clamped already? why?
       rot_y = 0
       rot_z = self.av_pitch % 360.0
   def get_pos(self):
       """ In minecraft, up is down, front is back, madness is sanity...
           Ok, it's more like x is x, y is z and z is y - because notch hates you
           This method does however return it in proper (x,y,z) format where z is height
       """
       while self.av_pos is None: eventlet.greenthread.sleep(0) # we can't return a position until we know where we are
       
       sane_x = self.av_pos[0]
       sane_y = self.av_pos[2]
       sane_z = self.av_pos[1]
       return sane_x,sane_y,sane_z
   def full_update(self):
       """ This is called every second (20 ticks)
       """
       # get the sane (x,y,z) position using get_pos() so it can handle blocking as required and then convert to minecraft
       sane_pos = self.get_pos()
       insane_x = sane_pos[0]
       insane_y = sane_pos[2]
       insane_z = sane_pos[1]
       # update player position at least once per second
       self.sock.send_player_position(buffer.Buffer.pack('ddd?',
            insane_x,
            insane_y,
            insane_z,
            True))
   def tick(self):
       cur_time = time.time()
       if (cur_time-self.last_tick) >= self.tick_delay:
          self.minecraft_client_tick()
          self.last_tick = cur_time
       if (cur_time - self.last_full_update) >= 1.0:
          self.full_update()
          self.last_full_update = cur_time
       eventlet.greenthread.sleep(self.tick_delay/2.0) # we actually want to check whether to tick
   def handle_login_success(self,buff):
       self.avatar_uuid = buff.unpack_string()
       self.avatar_name = buff.unpack_string()
       self.sock.switch_mode("play")
       yatelog.info('minecraft','Connected to minecraft server %s:%s with display name "%s" and avatar UUID %s' % (self.server_addr[0],self.server_addr[1],self.avatar_name,self.avatar_uuid))

driver = MinecraftDriver
