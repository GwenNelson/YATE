import eventlet
eventlet.monkey_patch()
import base
import utils
import yatelog
import time

from yateproto import *
from mcproto import mcsock
from mcproto import buffer

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
       self.dimension        = MC_OVERWORLD
       self.chunk_data       = {} # maps (x,z) (minecraft format) to chunk data for lazy evaluation
       self.env              = {} # voxels galore, in sane format for coordinates (x,y,z) but values are minecraft pallete entry indices
       self.vox_updates      = []
       self.sock.blocking_handlers = False
       yatelog.info('minecraft','Awaiting download of avatar position and terrain data')
       while self.av_pos is None:
          eventlet.greenthread.sleep(self.tick_delay)
          self.minecraft_client_tick()
       yatelog.info('minecraft','Got avatar position, awaiting chunks')
       while not self.chunk_data.has_key(self.get_av_chunk()):
          self.tick()
          yatelog.debug('minecraft','Waiting for chunk %s' % str(self.get_av_chunk()) )
          yatelog.debug('minecraft','Current avatar position: %s, Currently loaded chunks: %s' % (str(self.av_pos),str(self.chunk_data.keys())) )
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

       if not self.env.has_key((spatial_pos[0],spatial_pos[1],spatial_pos[2])): # if we don't have it, first try to get it from a chunk
          chunk_x,chunk_z = self.get_chunk_fromxz(spatial_pos[0],spatial_pos[1])
          yatelog.debug('minecraft','Do not have block %s, checking loaded chunks' % str(spatial_pos))
          if self.chunk_data.has_key((chunk_x,chunk_z)):
             yatelog.debug('minecraft','Found chunk (%s,%s) for %s' % (chunk_x,chunk_z,str(spatial_pos)))
             self.process_chunk_data(chunk_x,chunk_z,self.chunk_data[(chunk_x,chunk_z)])
             yatelog.debug('minecraft','Updated chunk (%s,%s)' % (chunk_x,chunk_z))
          else:
             yatelog.warn('minecraft','Queried block not in a currently loaded chunk at %s' % str(spatial_pos))
       # now we try and get it again

       if self.env.has_key((spatial_pos[0],spatial_pos[1],spatial_pos[2])):
          blockid = self.env[(spatial_pos[0],spatial_pos[1],spatial_pos[2])]
          if blockid >0:
             yate_type = YATE_VOXEL_TOTAL_OBSTACLE # temporary hack for now
          else:
             yate_type = YATE_VOXEL_EMPTY
       else:
          yate_type = YATE_VOXEL_UNKNOWN
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
       chunk_x        = buff.unpack_int()
       chunk_z        = buff.unpack_int()
       self.chunk_data[(chunk_x,chunk_z)] = buff
       self.chunk_data[(chunk_x,chunk_z)].save()
   def process_chunk_data(self,chunk_x,chunk_z,buff):
       """ Used for lazy evaluation
       """
       buff.restore()
       yatelog.debug('minecraft','Chunk update at (%s,%s)' % (chunk_x,chunk_z))
       continuous     = buff.unpack('?')
       primary_bitmap = buff.unpack_varint()
       data_size      = buff.unpack_varint()
       for chunk_y in xrange(16):
           eventlet.greenthread.sleep(0)
           chunk_blocks = []
           bits_per_block = 0
           pal_length     = 0
           pal_data       = []
           if primary_bitmap & (1 << chunk_y):
              bits_per_block = buff.unpack('B')

              if bits_per_block < 4: bits_per_block = 4
              if bits_per_block > 8: bits_per_block = 13
              pal_length     = buff.unpack_varint() # pallette length
              pal_data       = []
              if pal_length > 0:
                 for i in xrange(pal_length):
                     eventlet.greenthread.sleep(0)
                     pal_data.append(buff.unpack_varint())
              data_array_len = buff.unpack_varint()
              data_array = []
              for i in xrange(data_array_len):
                  eventlet.greenthread.sleep(0)
                  data_array.append(buff.unpack_long())
              max_val = (1 << bits_per_block) - 1
              for i in xrange(data_array_len):
                  eventlet.greenthread.sleep(0)
                  start_long   = (i * bits_per_block)
                  start_offset = (i * bits_per_block) % 64
                  end_long     = ((i + 1) * bits_per_block - 1)
                  if start_long == end_long:
                     block = (data_array[start_long/64] >> start_offset) & max_val
                  else:
                     end_offset = 64 - start_offset
                     block = (data_array[start_long/64] >> start_offset | data_array[end_long/64] << end_offset) & max_val
                  if pal_length >0:
                     if block > pal_length:
                        yatelog.warn('minecraft','Got a block outside of the chunk pallette, block ID is %s, pal length is %s' % (block,pal_length))
                     else:
                        block = pal_data[block-1]
                  chunk_blocks.append(block)
              lightcrap = buff.read(2048) # we just don't care about the lighting at all but still gotta read it
              if self.dimension==MC_OVERWORLD: lightcrap = buff.read(2048)
              block_offset = 0
              yatelog.debug('minecraft',str(len(chunk_blocks)))
              for block_x in xrange(16):
                  for block_z in xrange(16):
                      for block_y in xrange(16):
                          eventlet.greenthread.sleep(0)
                          if block_offset < 256:
                             total_block_x = block_x + (chunk_x*16)
                             total_block_y = block_y + (chunk_y*16)
                             total_block_z = block_z + (chunk_z*16)
                             sane_x = total_block_x
                             sane_y = total_block_z
                             sane_z = total_block_y
                             self.env[(sane_x,sane_y,sane_z)] = chunk_blocks[block_offset]
                             yatelog.debug('minecraft','Updated (%s,%s,%s) in chunk (%s,%s)' % (sane_x,sane_y,sane_z,chunk_x,chunk_z))
                             block_offset += 1
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
