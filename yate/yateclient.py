import eventlet
eventlet.monkey_patch()

import yatesock
import yatelog

import yateproto
from drivers import base
from yateproto import *

import time
import utils

class YATEMap:
   """ This class represents a voxel grid in 3D space and implements simple queries on that 3D space
       Entities are also tracked by this class
       This class should be considered read only outside of YATEClient unless you know what you're doing
   """
   def __init__(self,client):
       self.client = client
       self.voxels             = {}      # stores voxels
       self.entities           = {}      # stores entities
       self.avatar_spatial_pos = (0,0,0) # where the avatar is in 3D space
       self.visual_range_size  = (0,0,0) # the size of the visual range
       self.visual_range_start = (0,0,0) # specifies where the visible range of voxels starts in 3D space
       self.visual_range_end   = (0,0,0) # specifies where the visible range of voxels ends in 3D space
   def is_complete(self):
       """ returns a boolean value indicating whether or not the local visual range of voxels is complete
           this should be used just after connecting in a loop to get a full starting map
       """
       for x in xrange(self.visual_range_start[0],self.visual_range_end[0],1):
           for y in xrange(self.visual_range_start[1],self.visual_range_end[1],1):
               for z in xrange(self.visual_range_start[2],self.visual_range_end[2],1):
                   eventlet.greenthread.sleep(0)
                   if not self.voxels.has_key((x,y,z)):
                      self.client.send_request_voxel(x,y,z)
                      return False
       return True
   def set_visual_range(self,visual_range):
       """ Set the visual range - this assumes that the avatar position is already set
           If the avatar position is not set when this method is called then queries will fail until avatar position is updated to something accurate
       """
       self.visual_range_size = visual_range
       self.recalculate_visual()
   def get_avatar_pos(self):
       """ return the avatar position in 3D space, blocks if (0,0,0)
       """
       while self.avatar_spatial_pos == (0,0,0): eventlet.greenthread.sleep(0)
       self.recalculate_visual()
       return self.avatar_spatial_pos
   def set_avatar_pos(self,avatar_pos):
       """ Set the position of the AI avatar in 3D space
       """
       self.avatar_spatial_pos = tuple(avatar_pos)
       self.recalculate_visual()
   def recalculate_visual(self):
       """ Used internally to recalculate the visual range area
       """
       avatar_x,avatar_y,avatar_z = self.avatar_spatial_pos
       start_x = avatar_x - (self.visual_range_size[0]/2)
       start_y = avatar_y - (self.visual_range_size[1]/2)
       start_z = avatar_z
       end_x   = start_x  + self.visual_range_size[0]
       end_y   = start_y  + self.visual_range_size[1]
       end_z   = start_z  + self.visual_range_size[2]
       self.visual_range_start = (start_x,start_y,start_z)
       self.visual_range_end   = (end_x,end_y,end_z)
   def get_voxel(self,spatial_pos):
       """ Return the voxel object found at the specified coordinates
           If this is within the visible area and we do not know anything about the specified voxel then the call blocks until we know at least whether or not there's an unknown voxel there on the server side
           If this is outside the visible area and we do not know anything about the specified voxel then the call returns an unknown voxel
       """
       if utils.check_within(spatial_pos,self.visual_range_start,self.visual_range_end):
          if not self.voxels.has_key(spatial_pos):
             self.send_request_voxel(*spatial_pos)
             while not self.voxels.has_key(spatial_pos):
                eventlet.greenthread.sleep(0)
       if self.voxels.has_key(spatial_pos): return self.voxels[spatial_pos]
       return base.YateBaseVoxel(spatial_pos=spatial_pos,basic_type=YATE_VOXEL_UNKNOWN)
   def is_visible(self,spatial_pos):
       """ Returns true if the specified coordinates are inside the visual range
       """
       if utils.check_within(spatial_pos,self.visual_range_start,self.visual_range_end):
          return True
       return False
   def set_voxel(self,voxel):
       """ Sets a voxel - takes a voxel object (see base.py) and updates the map with that object
       """
       self.voxels[voxel.get_pos()] = voxel

class YATEClient:
   """ This class is used to connect to a YATE proxy server
   """

   def __init__(self,server_addr=None,connect_cb=None,disconnect_cb=None,voxel_update_cb=None,avatar_pos_cb=None):
       """ server_addr is a tuple of (ip,port) - this should usually be something on localhost for security reasons
           connect_cb and disconnect_cb are callback functions that will be invoked upon successful connect/disconnect - they have no params
           voxel_update_cb is called when a voxel update is received and is passed a voxel object as the only parameter
           avatar_pos_cb   is called when the AI avatar moves and is passed a tuple representing the new coordinates
       """
       self.server_addr     = server_addr
       self.connected       = False
       self.ready           = False
       self.connect_id      = None
       self.connect_cb      = connect_cb
       self.disconnect_cb   = disconnect_cb
       self.voxel_update_cb = voxel_update_cb
       self.avatar_pos_cb   = avatar_pos_cb
       self.sock            = yatesock.YATESocket()
       self.pool = eventlet.GreenPool(1000)
       self.handlers = {MSGTYPE_CONNECT_ACK:  self.handle_connect_ack,
                        MSGTYPE_VISUAL_RANGE: self.handle_visual_range,
                        MSGTYPE_VOXEL_UPDATE: self.handle_voxel_update,
                        MSGTYPE_AVATAR_POS:   self.handle_avatar_pos}
       if self.server_addr != None: self.connect_to(self.server_addr)
       self.envmap = YATEMap(self)
       self.last_update = 0

   def move_vector(self,v):
       """ Send a request to move in the specified vector if possible
       """
       self.sock.send_move_vector(*v)
   def get_map(self):
       """ Return the map used by shis client - this should be treated as read only outside of the client class
       """
       return self.envmap
   def mark_dirty(self):
       """ Marks the local world model as dirty - this forces a full update
       """
       self.last_update = 0
   def mark_updated(self):
       """ Marks the local world model as updated
       """
       self.last_update = time.time()
   def get_port(self):
       return self.sock.get_endpoint()[1]
   def refresh_vis(self,voxel_pos=None,entity_id=None):
       """ Call this to request a refresh of the visual perceptions
           This will only update what is within visual range of the AI's avatar and it is only a request - the request may not be honoured
           A decent AGI will be able to use this to build a probablistic model of the environment so the unreliable nature is by design
           If voxel_pos is a tuple of 3D coordinates, a single voxel will be requested for update
           If entity_id is an entity UUID string, the relevant entity will be requested for update
           The client keeps track of the last time it received a packet that updates the world model and tells the server of that time
           The server will only send updates if that time has passed unless the client requests a single voxel or entity
       """
       if voxel_pos != None:
          self.sock.send_request_voxel(voxel_pos)
          return
       if entity_id != None:
          self.sock.send_request_entity(entity_id)
          return
       if not self.envmap.is_complete():
          self.mark_dirty()
       self.send_request_visual(self.last_update)
   def handle_visual_range(self,msg_params,from_addr,msg_id):
       self.envmap.set_visual_range(msg_params)
       self.mark_updated()
   def handle_voxel_update(self,msg_params,from_addr,msg_id):
       new_vox = base.YateBaseVoxel(from_params = msg_params)
       self.envmap.set_voxel(new_vox)
       self.mark_updated()
       if self.voxel_update_cb != None: self.voxel_update_cb(new_vox)
   def handle_avatar_pos(self,msg_params,from_addr,msg_id):
       self.envmap.set_avatar_pos(msg_params)
       self.mark_updated()
       if self.avatar_pos_cb != None: self.avatar_pos_cb(msg_params)
   def handle_connect_ack(self,msg_params,msg_id):
       yatelog.info('YATEClient','Successfully connected to server')
       self.ready = True
       if self.connect_cb != None: self.connect_cb()
       self.pool.spawn_n(self.do_keepalive)
   def do_keepalive(self):
       while self.ready:
          eventlet.greenthread.sleep(YATE_KEEPALIVE_TIMEOUT+1)
          if not self.sock.is_connected(self.server_addr):
             yatelog.info('YATEClient','Timed out server')
             self.ready     = False
             self.connected = False
             if self.disconnect_cb != None: self.disconnect_cb()
   def stop(self):
       """ Stop the client - terminate any threads and close the socket cleanly
       """
       self.ready = False
       self.sock.stop()
       self.pool.waitall()
       self.server_addr = None
   def is_connected(self):
       """ returns a boolean value indicating whether or not we're connected AND ready to talk to the proxy
       """
       if self.server_addr == None: return False
       if not self.sock.is_connected(self.server_addr): return False
       if not self.ready: return False
       return True
   def connect_to(self,server_addr):
       """ if a server address was not passed into __init__, use this to connect
       """
       yatelog.info('YATEClient','Connecting to server at %s:%s' % server_addr)
       self.server_addr = server_addr
       self.sock.connect_to(server_addr)
