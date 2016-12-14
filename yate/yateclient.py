import eventlet
eventlet.monkey_patch()

import socket
import yatelog

import yateproto
from yateproto import *

class YATEMethod:
   """ Wrapper used to dynamically call methods that transmit a message, for the win
   """
   def __init__(self,client,msgtype):
       self.msgtype = msgtype
       self.client  = client
   def __call__(self,*params):
       return send_yate_msg(self.msgtype,params,self.client.server_addr,self.client.sock)

class YATEClient:
   """ This class is used to connect to a YATE proxy server
   """

   def __init__(self,server_addr=None,connect_cb=None,disconnect_cb=None):
       """ server_addr is a tuple of (ip,port) - this should usually be something on localhost for security reasons
           connect_cb and disconnect_cb are callback functions that will be invoked upon successful connect/disconnect
       """
       self.server_addr   = server_addr
       self.connected     = False
       self.ready         = False
       self.connect_id    = None
       self.connect_cb    = connect_cb
       self.disconnect_cb = disconnect_cb
       self.sock        = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
       self.sock.bind(('127.0.0.1',0))
       self.pool = eventlet.GreenPool(100)
       self.last_acked = set()
       self.in_q = eventlet.queue.LightQueue()
       self.handlers = {MSGTYPE_CONNECT_ACK:  self.handle_connect_ack,
                        MSGTYPE_KEEPALIVE:    self.handle_keepalive,
                        MSGTYPE_KEEPALIVE_ACK:self.handle_keepalive_ack}
       if self.server_addr != None: self.connect_to(self.server_addr)

   def __getattr__(self,name):
       """ This is used to implement message stuff in a hackish way
       """
       if name.startswith('send_'):
          msgtype_name = 'MSGTYPE_%s' % (name[5:].upper())
          if hasattr(yateproto,msgtype_name):
             return YATEMethod(self,getattr(yateproto,msgtype_name))
   def get_port(self):
       return self.sock.getsockname()[1]
   def refresh_vis(self,spatial_pos=None,entity_id=None):
       """ Call this to request a refresh of the visual perceptions
           This will only update what is within visual range of the AI's avatar and it is only a request - the request may not be honoured
           A decent AGI will be able to use this to build a probablistic model of the environment so the unreliable nature is by design
           If spatial_pos is a tuple of 3D coordinates, a single voxel will be requested for update
           If entity_id is an entity UUID string, the relevant entity will be requested for update
       """
       pass
   def handle_keepalive(self,msg_params,addr,msg_id):
       send_yate_msg(MSGTYPE_KEEPALIVE_ACK,[msg_id],addr,self.sock)
   def handle_keepalive_ack(self,msg_params,addr,msg_id):
       self.last_acked.add(msg_params[0])
   def handle_connect_ack(self,msg_params,addr,msg_id):
       yatelog.info('YATEClient','Successfully connected to server')
       self.ready = True
       self.pool.spawn_n(self.do_keepalive)
       if self.connect_cb != None: self.connect_cb()
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
             if self.disconnect_cb != None: self.disconnect_cb()
   def proc_packets(self):
       while self.connected:
          eventlet.greenthread.sleep(0)
          data,addr = self.in_q.get(block=True)
          try:
             parsed_data = msgpack.unpackb(data)
             msg_type    = parsed_data[0]
             msg_params  = parsed_data[1]
             msg_id      = parsed_data[2]
             yatelog.debug('YATEClient','Got message %s from %s:%s' % (str([msgtype_str[msg_type],msg_params,msg_id]),addr[0],addr[1]))
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
       """ returns a boolean value indicating whether or not we're connected AND ready to talk to the proxy
       """
       if self.server_addr == None: return False
       if not self.connected: return False
       if not self.ready: return False
       return True
   def connect_to(self,server_addr):
       """ if a server address was not passed into __init__, use this to connect
       """
       yatelog.info('YATEClient','Connecting to server at %s:%s' % server_addr)
       self.server_addr = server_addr
       self.connected = True
       self.pool.spawn_n(self.read_packets)
       for x in xrange(10): self.pool.spawn_n(self.proc_packets)
       self.connect_id  = send_yate_msg(MSGTYPE_CONNECT,(),server_addr,self.sock)

