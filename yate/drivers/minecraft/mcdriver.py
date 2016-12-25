import eventlet
eventlet.monkey_patch()
import base
import utils
import yatelog
import time

from yateproto import *
from mcproto import mcsock
from mcproto import buffer

from mcproto import smpmap
import burger_data

MC_OVERWORLD = 1

class MinecraftDriver(base.YateBaseDriver):
   def __init__(self,username=None,password=None,server='127.0.0.1:25565'):
       super(MinecraftDriver,self).__init__(username=username,password=password,server=server)
       self.username    = username
       self.password    = password
       self.avatar_uuid = None
       self.avatar_eid  = 0
       self.avatar_name = username # not always the same, just usually
       server_ip,server_port = server.split(':')
       self.server_addr = (server_ip,int(server_port))
       yatelog.info('minecraft','Minecraft driver starting up')
   
       pack_handlers = {'login_success':           self.handle_login_success,
                        'join_game':               self.handle_join_game,
                        'player_position_and_look':self.handle_player_position_and_look,
                        'chunk_data':              self.handle_chunk_data}

       self.sock = mcsock.MCSocket(self.server_addr,handlers=pack_handlers,display_name=username)
       self.sock.switch_mode(mcsock.protocol_modes['login'])
       self.tick_delay       = (1.0/20.0)
       self.last_tick        = time.time() - self.tick_delay # make sure that we tick after connecting
       self.last_full_update = time.time() - 1.0             # make sure we run a full update after connecting
       self.av_pos           = None # stores the avatar position, in minecraft format also known as (x,z,y) to sane humans
       self.av_pitch         = None
       self.av_yaw           = None
       self.on_ground        = True
       self.world            = smpmap.Dimension(smpmap.DIMENSION_OVERWORLD)
       self.sock.blocking_handlers = False
       yatelog.info('minecraft','Awaiting download of avatar position and terrain data')
       while self.av_pos is None:
          eventlet.greenthread.sleep(self.tick_delay)
          self.minecraft_client_tick()
       yatelog.info('minecraft','Got avatar position, awaiting chunks')
       while self.world.get_block(self.av_pos[0],self.av_pos[2],self.av_pos[1]) is None:
          self.tick()
          yatelog.debug('minecraft','Waiting for chunk %s' % str(self.get_av_chunk()) )
       yatelog.info('minecraft','Got terrain data, ready to rock')
   def get_chunk_fromxz(self,x,z):
       """ Util function to get what chunk an (x,z) coordinate is in, minecraft format - returns (x,z)
       """
       chunk_x = int(float(x) / 16.0)
       chunk_z = int(float(z) / 16.0)
       return (chunk_x,chunk_z)
   def get_av_chunk(self):
       return self.get_chunk_fromxz(self.av_pos[0],self.av_pos[2])
   def get_voxel(self,spatial_pos):
       yatelog.debug('minecraft','Querying block at %s' % str(spatial_pos))
       insane_x = spatial_pos[0]
       insane_y = spatial_pos[2]
       insane_z = spatial_pos[1]
       block = self.world.get_block(insane_x,insane_y,insane_z)
       if block is None:
          yate_type = YATE_VOXEL_UNKNOWN
       else:
          blockid = block[0]
          if blockid >0:
             yate_type = YATE_VOXEL_TOTAL_OBSTACLE
          else:
             yate_type = YATE_VOXEL_EMPTY
       # now we try and get it again

       if yate_type != YATE_VOXEL_UNKNOWN:
          blockdata = burger_data.blockid_blocks[blockid]
          yatelog.debug('minecraft','Block at %s: %s' % (str(spatial_pos),blockdata))
          vox = base.YateBaseVoxel(spatial_pos=tuple(spatial_pos),basic_type=yate_type,specific_type=blockid)
       else:
          yatelog.debug('minecraft','Unknown block at %s' % (str(spatial_pos)))
          vox = base.YateBaseVoxel(spatial_pos=tuple(spatial_pos),basic_type=YATE_VOXEL_UNKNOWN)
       return vox
   def get_vision_range(self):
       """ Minecraft chunk sections are 16*16*16 - this would probably be the ideal if it could fit into a single bulk voxel update
           Sadly it can't, so we return half of that on the (X,Y) plane and a quarter on the Z axis or 8*8*4
       """
       return (8,8,4)
   def minecraft_client_tick(self):
       """ This is called 20 times per second and does per-tick things
       """
       self.sock.send_player(buffer.Buffer.pack('?', True)) # send a Player packet every tick
   def handle_chunk_data(self,buff):
       """ We get some voxel data here, yay!
       """
       data = {}
       data['chunk_x']        = buff.unpack_int()
       data['chunk_z']        = buff.unpack_int()
       data['continuous']     = buff.unpack('?')
       data['primary_bitmap'] = buff.unpack_varint()
       data['data_size']      = buff.unpack_varint()
       data['data']           = buff.read()
       self.world.unpack_column(data)
   def handle_join_game(self,buff):
       self.avatar_eid = buff.unpack_int()
       yatelog.info('minecraft','We are entity ID %s' % self.avatar_eid)
       self.sock.send_plugin_message(buffer.Buffer.pack_string('MC|Brand'),
                                     buffer.Buffer.pack_string('YATE minecraft driver'))
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
          for i in xrange(0,3):
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
             self.av_pitch  = pos_look[4] # absolute pitch is better in music, and kinda neutral in 3D game network protocols
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
       # if we're using blocking handlers, return immediately
       if self.sock.blocking_handlers: return
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
       if not (self.sock.protocol_mode == mcsock.protocol_modes['play']): return
       if (cur_time-self.last_tick) >= self.tick_delay:
          self.minecraft_client_tick()
          self.last_tick = cur_time
       if (cur_time - self.last_full_update) >= 1.0:
          self.full_update()
          self.last_full_update = cur_time
       end_time = time.time()
       if end_time-cur_time <= self.tick_delay:
          eventlet.greenthread.sleep(self.tick_delay-end_time-cur_time) # this should make updates very slightly mildly smoother, but only a little bit
       else:
          yatelog.warn('minecraft','tick took longer than the standard tick delay - this usually indicates you need a better CPU or better coding skills')
   def handle_login_success(self,buff):
       self.avatar_uuid = buff.unpack_string()
       self.avatar_name = buff.unpack_string()
       self.sock.switch_mode("play")
       yatelog.info('minecraft','Connected to minecraft server %s:%s with display name "%s" and avatar UUID %s' % (self.server_addr[0],self.server_addr[1],self.avatar_name,self.avatar_uuid))
       self.sock.send_client_settings(buffer.Buffer.pack_string('en_GB'), # locale
                                      buffer.Buffer.pack_byte(1),         # view distance
                                      buffer.Buffer.pack_varint(0),       # chat is enabled
                                      buffer.Buffer.pack('?',False),      # disable chat colors
                                      buffer.Buffer.pack_byte(0xFF),      # enable all the displayed skin parts
                                      buffer.Buffer.pack_varint(1))       # right handed, not sure if this matters

driver = MinecraftDriver
