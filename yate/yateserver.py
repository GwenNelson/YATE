import eventlet
eventlet.monkey_patch()
import sys
import yatelog
import yatesock
import time
import msgpack
import logging

import utils # yate utils
from yateproto import *

class YATEServer:
   def __init__(self,driver,verbose=False):
       self.logger   = yatelog.get_logger()
       if verbose: self.logger.setLevel(logging.DEBUG)
       self.driver   = driver

       self.handlers = {MSGTYPE_REQUEST_POS:       self.handle_request_pos,
                        MSGTYPE_REQUEST_RANGE:     self.handle_request_range,
                        MSGTYPE_REQUEST_VOXEL:     self.handle_request_voxel,
                        MSGTYPE_VISIBLE_VOXEL_REQ: self.handle_visible_voxel_req,
                        MSGTYPE_MOVE_VECTOR:   self.handle_move_vector}
       self.sock              = yatesock.YATESocket(handlers=self.handlers)
       self.pool              = eventlet.GreenPool(1000)
       self.pool.spawn(self.do_ticks)
       self.pool.spawn(self.do_vis_updates)
   def do_ticks(self):
       d = self.driver
       while True:
          eventlet.greenthread.sleep(0)
          try:
             d.tick()
          except:
             yatelog.minor_exception('YATEServer','Failed driver tick')
   def do_vis_updates(self):
       visual_range = self.driver.get_vision_range()
       while True:
          eventlet.greenthread.sleep(0.5)
          self.update_vis_voxels()
   def update_vis_voxels(self):
       visual_range   = self.driver.get_vision_range()
       avatar_pos     = self.driver.get_pos()
       bulkdata = []
       for vox_pos in utils.iter_within(*utils.calc_range(avatar_pos,visual_range)):
           eventlet.greenthread.sleep(0)
           bulkdata.append(  (self.driver.get_voxel(vox_pos).as_msgparams())  )
       self.sock.send_bulk_voxel_update(*bulkdata)
   def handle_request_pos(self,msg_params,from_addr,msg_id):
       pos = self.driver.get_pos()
       self.sock.send_avatar_pos(pos[0],pos[1],pos[2],to_addr=from_addr)
   def handle_request_range(self,msg_params,from_addr,msg_id):
       visual_range = self.driver.get_vision_range()
       self.sock.send_visual_range(*visual_range, to_addr=from_addr)
   def handle_request_voxel(self,msg_params,from_addr,msg_id):
       voxel_data = self.driver.get_voxel(msg_params)
       self.send_voxel_update(voxel_data.as_msgparams())
   def handle_visible_voxel_req(self,msg_params,from_addr,msg_id):
       self.update_vis_voxels()
   def handle_move_vector(self,msg_params,from_addr,msg_id):
       self.driver.move_vector(msg_params)
       pos = self.driver.get_pos()
       self.sock.send_avatar_pos(pos[0],pos[1],pos[2],to_addr=from_addr)
   def get_port(self):
       return self.sock.get_endpoint()[1]

