import eventlet
eventlet.monkey_patch()

import socket
import yatelog

from yateproto import *

class YATEClient:
   def __init__(self,server_addr=None):
       self.server_addr = server_addr
       self.connected   = False
       self.ready       = False
       self.connect_id  = None
       self.sock        = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
       self.sock.bind(('127.0.0.1',0))
       self.pool = eventlet.GreenPool(100)
       self.last_acked = set()
       self.in_q = eventlet.queue.LightQueue()
       self.handlers = {MSGTYPE_CONNECT_ACK:  self.handle_connect_ack,
                        MSGTYPE_KEEPALIVE:    self.handle_keepalive,
                        MSGTYPE_KEEPALIVE_ACK:self.handle_keepalive_ack}
       if self.server_addr != None: self.connect_to(self.server_addr)

   def get_port(self):
       return self.sock.getsockname()[1]
   def handle_keepalive(self,msg_params,addr,msg_id):
       send_yate_msg(MSGTYPE_KEEPALIVE_ACK,[msg_id],addr,self.sock)
   def handle_keepalive_ack(self,msg_params,addr,msg_id):
       self.last_acked.add(msg_params[0])
   def handle_connect_ack(self,msg_params,addr,msg_id):
       yatelog.info('YATEClient','Successfully connected to server')
       self.ready = True
       self.pool.spawn_n(self.do_keepalive)
   def do_keepalive(self):
       last_id = 1
       while self.ready:
          self.last_acked.discard(last_id)
          last_id = send_yate_msg(MSGTYPE_KEEPALIVE,[],self.server_addr,self.sock)
          eventlet.greenthread.sleep(YATE_KEEPALIVE_TIMEOUT)
          if not (last_id in self.last_acked):
             yatelog.info('YATEClient','Timed out server')
             self.ready     = False
             self.connected = False
   def proc_packets(self):
       while self.connected:
          eventlet.greenthread.sleep(0)
          data,addr = self.in_q.get(block=True)
          try:
             parsed_data = msgpack.unpackb(data)
             msg_type    = parsed_data[0]
             msg_params  = parsed_data[1]
             msg_id      = parsed_data[2]
             yatelog.info('YATEClient','Got message %s from %s' % (msg_type,addr))
             if addr != self.server_addr:
                send_yate_msg(MSGTYPE_UNKNOWN_PEER,[],addr,self.sock)
             elif self.handlers.has_key(msg_type):
                self.handlers[msg_type](msg_params,addr,msg_id)
          except Exception,e:
             yatelog.minor_exception('YATEServer','Error parsing packet from server') 
   def read_packets(self):
       yatelog.info('YATEClient','Bound local port at %s' % self.get_port())
       while self.connected:
          eventlet.greenthread.sleep(0)
          data,addr = self.sock.recvfrom(8192)
          self.in_q.put([data,addr])
   def stop(self):
       """ Stop the client - terminate any threads and close the socket cleanly
       """
       self.connected = False
       self.pool.waitall()
       self.sock.shutdown()
   def is_connected(self):
       if self.server_addr == None: return False
       if not self.connected: return False
       if not self.ready: return False
       return True
   def connect_to(self,server_addr):
       yatelog.info('YATEClient','Connecting to server at %s:%s' % server_addr)
       self.server_addr = server_addr
       self.connected = True
       self.pool.spawn_n(self.read_packets)
       for x in xrange(10): self.pool.spawn_n(self.proc_packets)
       self.connect_id  = send_yate_msg(MSGTYPE_CONNECT,(),server_addr,self.sock)

