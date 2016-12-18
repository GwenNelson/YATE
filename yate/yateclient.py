import eventlet
eventlet.monkey_patch()

import yatesock
import yatelog

import yateproto
from drivers import base
from yateproto import *

import time
import utils

UPDATE_DELAY=0.1

class YATEClient:
   """ This class is used to connect to a YATE proxy server
   """

   def __init__(self,server_addr=None,connect_cb=None,disconnect_cb=None,voxel_update_cb=None,avatar_pos_cb=None):
       """ server_addr is a tuple of (ip,port) - this should usually be something on localhost for security reasons
           connect_cb and disconnect_cb are callback functions that will be invoked upon successful connect/disconnect - they have no params
           voxel_update_cb is called when a visible voxel is updated and is passed a voxel object as the only parameter
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
       self.avatar_pos      = None
       self.pool = eventlet.GreenPool(1000)
       self.handlers = {MSGTYPE_CONNECT_ACK:       self.handle_connect_ack,
                        MSGTYPE_VISUAL_RANGE:      self.handle_visual_range,
                        MSGTYPE_VOXEL_UPDATE:      self.handle_voxel_update,
                        MSGTYPE_BULK_VOXEL_UPDATE: self.handle_bulk_voxel,
                        MSGTYPE_AVATAR_POS:        self.handle_avatar_pos}
       self.sock         = yatesock.YATESocket(handlers=self.handlers)
       self.visual_range = None
       if self.server_addr != None: self.connect_to(self.server_addr)
   def move_vector(self,v):
       """ Send a request to move in the specified vector if possible
       """
       self.sock.send_move_vector(*v,to_addr = self.server_addr)
   def get_port(self):
       return self.sock.get_endpoint()[1]
   def handle_bulk_voxel(self,msg_params,from_addr,msg_id):
       """ bulk voxel updates are preferred for performance reasons
       """
       for voxel in msg_params:
           self.handle_voxel_update(voxel,from_addr,msg_id)
   def handle_visual_range(self,msg_params,from_addr,msg_id):
       """ update the visual range so we can limit queries appropriately
       """
       self.visual_range = msg_params
   def handle_voxel_update(self,msg_params,from_addr,msg_id):
       """ handle single voxel updates
       """
       new_vox = base.YateBaseVoxel(from_params = msg_params)
       yatelog.debug('YATEClient','Updating voxel: %s' % str(new_vox))
       if self.voxel_update_cb != None: self.voxel_update_cb(new_vox)
   def handle_avatar_pos(self,msg_params,from_addr,msg_id):
       """ handle avatar position updates
       """
       self.avatar_pos = msg_params
       if self.avatar_pos_cb != None: self.avatar_pos_cb(self.avatar_pos)
   def handle_connect_ack(self,msg_params,from_addr,msg_id):
       yatelog.info('YATEClient','Successfully connected to server')
       self.ready = True
       self.pool.spawn_n(self.do_keepalive)
       self.pool.spawn_n(self.do_updates)
       if self.connect_cb != None: self.connect_cb()

   def do_updates(self):
       while self.ready:
          self.sock.send_visible_voxel_req(to_addr=self.server_addr)
          self.sock.send_request_pos(to_addr=self.server_addr)
          eventlet.greenthread.sleep(UPDATE_DELAY)
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
