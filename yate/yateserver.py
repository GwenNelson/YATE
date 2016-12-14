import eventlet
eventlet.monkey_patch()
import sys
import yatelog
import imp
import socket
import time
import msgpack

from yateproto import *

class YATEServer:
   def __init__(self,driver):
       self.logger   = yatelog.get_logger()
       self.driver   = driver
       self.sock     = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
       self.pool     = eventlet.GreenPool(2000)
       self.in_q     = eventlet.queue.LightQueue()
       self.clients  = {}
       self.handlers = {MSGTYPE_KEEPALIVE:     self.handle_keepalive,
                        MSGTYPE_CONNECT:       self.handle_connect,
                        MSGTYPE_KEEPALIVE_ACK: self.handle_keepalive_ack,
                        MSGTYPE_REQUEST_VISUAL:self.handle_request_visual,
                        MSGTYPE_REQUEST_VOXEL: self.handle_request_voxel,
                        MSGTYPE_MOVE_VECTOR:   self.handle_move_vector}
       self.handlers.update(self.driver.get_msg_handlers())
       self.sock.bind(('127.0.0.1',0))
       self.pool.spawn_n(self.read_packets)
       for x in xrange(100): self.pool.spawn_n(self.proc_packets)
   def handle_move_vector(self,msg_params,from_addr,msg_id):
       self.driver.move_vector(tuple(msg_params))
       send_yate_msg(MSGTYPE_AVATAR_POS,self.driver.get_pos(),from_addr,self.sock)
   def handle_request_voxel(self,msg_params,from_addr,msg_id):
       self.send_voxel_update(msg_params,from_addr)
   def handle_request_visual(self,msg_params,from_addr,msg_id):
       yatelog.debug('YATEServer','Client requesting visual perception update')

       check_time = msg_params[0] # the timestamp given in the packet to compare against
       if self.driver.changed_since(check_time):
          yatelog.debug('YATEServer','Sending updates to client due to out of date timestamp %s' % time.ctime(check_time))
          visual_range = self.driver.get_vision_range()
          send_yate_msg(MSGTYPE_VISUAL_RANGE,visual_range,from_addr,self.sock)

          avatar_pos   = self.driver.get_pos()
          send_yate_msg(MSGTYPE_AVATAR_POS,avatar_pos,from_addr,self.sock)
       
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
       send_yate_msg(MSGTYPE_VOXEL_UPDATE,voxel_data.as_msgparams(),client_addr,self.sock)
   def handle_connect(self,msg_params,from_addr,msg_id):
       self.clients[tuple(from_addr)] = {YATE_LAST_ACKED:set()}

       self.pool.spawn_n(self.do_keepalive,from_addr)

       send_yate_msg(MSGTYPE_CONNECT_ACK,[],from_addr,self.sock)
       yatelog.info('YATEServer','New client at %s:%s' % from_addr)
   def do_keepalive(self,client_addr):
       """ This function handles sending keep alives to the client and killing it if
           the keep alive times out
       """
       while self.clients.has_key(tuple(client_addr)):
          last_id = send_yate_msg(MSGTYPE_KEEPALIVE,[],client_addr,self.sock)
          eventlet.greenthread.sleep(YATE_KEEPALIVE_TIMEOUT)
          if self.clients.has_key(tuple(client_addr)):
             if not last_id in self.clients[tuple(client_addr)][YATE_LAST_ACKED]:
                del self.clients[tuple(client_addr)]
             else:
                self.clients[tuple(client_addr)][YATE_LAST_ACKED].remove(last_id)
   def handle_keepalive_ack(self,msg_params,from_addr,msg_id):
       self.clients[tuple(from_addr)][YATE_LAST_ACKED].add(msg_params[0])
   def handle_keepalive(self,msg_params,from_addr,msg_id):
       send_yate_msg(MSGTYPE_KEEPALIVE_ACK,[msg_id],from_addr,self.sock)
   def get_port(self):
       return self.sock.getsockname()[1]
   def proc_packets(self):
       while True:
         eventlet.greenthread.sleep(0)
         try:
            data,addr   = self.in_q.get_nowait()
            parsed_data = msgpack.unpackb(data)
            msg_type    = parsed_data[0]
            msg_params  = parsed_data[1]
            msg_id      = parsed_data[2]
            if not self.clients.has_key(tuple(addr)):
               if msg_type != MSGTYPE_CONNECT:
                  send_yate_msg(MSGTYPE_UNKNOWN_PEER,[],addr,self.sock)
               else:
                  self.handle_connect(msg_params,addr,msg_id)
            else:
               if self.handlers.has_key(msg_type):
                  yatelog.debug('YATEServer','Message %s from %s:%s' % (str([msgtype_str[msg_type],msg_params,msg_id]),addr[0],addr[1]))
                  try:
                     self.handlers[msg_type](msg_params,addr,msg_id)
                  except:
                     yatelog.minor_exception('YATEServer','Error during message handling')
               else:
                  yatelog.warn('YATEClient','Unhandled message %s from %s:%s' % (str([msgtype_str[msg_type],msg_params,msg_id]),addr[0],addr[1]))
         except:
            pass
   def read_packets(self):
       """ Do the minimal amount of work possible here and dispatch to a green thread for handling
       """
       while True:
         eventlet.greenthread.sleep(0)
         try:
            data,addr = self.sock.recvfrom(8192)
            self.in_q.put_nowait([data,tuple(addr)])
         except:
            pass

