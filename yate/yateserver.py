import eventlet
eventlet.monkey_patch()
import sys
import yatelog
import yatesock
import time
import msgpack

from yateproto import *

class YATEServer:
   def __init__(self,driver):
       self.logger   = yatelog.get_logger()
       self.driver   = driver

       self.clients  = {}
       self.handlers = {MSGTYPE_REQUEST_VISUAL:self.handle_request_visual,
                        MSGTYPE_REQUEST_VOXEL: self.handle_request_voxel,
                        MSGTYPE_MOVE_VECTOR:   self.handle_move_vector}
       self.handlers.update(self.driver.get_msg_handlers())
       self.sock     = yatesock.YATESocket(handlers=self.handlers)
   def handle_move_vector(self,msg_params,from_addr,msg_id):
       self.driver.move_vector(tuple(msg_params))
       self.sock.send_avatar_pos(self.driver.get_pos(),to_addr=from_addr)
   def handle_request_voxel(self,msg_params,from_addr,msg_id):
       self.send_voxel_update(msg_params,from_addr)
   def handle_request_visual(self,msg_params,from_addr,msg_id):
       yatelog.debug('YATEServer','Client requesting visual perception update')

       check_time = msg_params[0] # the timestamp given in the packet to compare against
       if self.driver.changed_since(check_time):
          yatelog.debug('YATEServer','Sending updates to client due to out of date timestamp %s' % time.ctime(check_time))
          visual_range = self.driver.get_vision_range()
          self.sock.send_visual_range(*visual_range, to_addr=from_addr)

          avatar_pos   = self.driver.get_pos()
          self.sock.send_avatar_pos(*avatar_pos,to_addr=from_addr)
       
          # calculate where the visible voxels begin and end
          start_x = avatar_pos[0]-(visual_range[0]/2)
          start_y = avatar_pos[1]-(visual_range[1]/2)
          start_z = avatar_pos[2]
          end_x   = start_x + visual_range[0]
          end_y   = start_y + visual_range[1]
          end_z   = start_z + visual_range[2]
          yatelog.debug('YATEServer','Visual range: (%s %s %s)-(%s %s %s), avatar at %s' % (start_x,start_y,start_z,end_x,end_y,end_z,avatar_pos))
       
          # send some voxel updates
          for x in xrange(start_x-1,end_x,1):
              for y in xrange(start_y-1,end_y,1):
                  for z in xrange(start_z,end_z,1):
                      voxel_pos  = (x,y,z)
                      eventlet.greenthread.sleep(0)
                      self.send_voxel_update(voxel_pos,from_addr)

   def send_voxel_update(self,voxel_pos,client_addr):
       yatelog.debug('YATEServer','Updating voxel at %s' % str(voxel_pos))
       voxel_data = self.driver.get_voxel(voxel_pos)
       msgparams  = voxel_data.as_msgparams()
       self.sock.send_voxel_update(*msgparams,to_addr=client_addr)
   def get_port(self):
       return self.sock.get_endpoint()[1]

