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
       self.pool     = eventlet.GreenPool(100)
       self.in_q     = eventlet.queue.LightQueue()
       self.clients  = {}
       self.handlers = {MSGTYPE_KEEPALIVE:    self.handle_keepalive,
                        MSGTYPE_CONNECT:      self.handle_connect,
                        MSGTYPE_KEEPALIVE_ACK:self.handle_keepalive_ack}
       self.handlers.update(self.driver.get_msg_handlers())
       self.sock.bind(('127.0.0.1',0))
       self.pool.spawn_n(self.read_packets)
       for x in xrange(10): self.pool.spawn_n(self.proc_packets)
   def handle_connect(self,msg_params,from_addr,msg_id):
       self.clients[from_addr] = {YATE_LAST_ACKED:set()}
       self.pool.spawn_n(self.do_keepalive,from_addr)
       send_yate_msg(MSGTYPE_CONNECT_ACK,(msg_id),from_addr,self.sock)
       yatelog.info('YATEServer','New client at %s:%s' % from_addr)
   def do_keepalive(self,client_addr):
       """ This function handles sending keep alives to the client and killing it if
           the keep alive times out
       """
       while self.clients.has_key(client_addr):
          last_id = send_yate_msg(MSGTYPE_KEEPALIVE,(),client_addr,self.sock)
          eventlet.greenthread.sleep(YATE_KEEPALIVE_TIMEOUT)
          if self.clients.has_key(client_addr):
             if not last_id in self.clients[client_addr][YATE_LAST_ACKED]:
                del self.clients[client_addr]
   def handle_keepalive_ack(self,msg_params,from_addr,msg_id):
       self.clients[from_addr][YATE_LAST_ACKED].add(msg_id)
   def handle_keepalive(self,msg_params,from_addr,msg_id):
       send_yate_msg(MSGTYPE_KEEPALIVE_ACK,(msg_id),from_addr,self.sock)
   def get_port(self):
       return self.sock.getsockname()[1]
   def proc_packets(self):
       while True:
         data,addr = self.in_q.get(block=True)
         try:
            parsed_data = msgpack.unpackb(data)
            msg_type    = parsed_data[0]
            msg_params  = parsed_data[1]
            msg_id      = parsed_data[2]
            if not self.clients.has_key(addr):
               if msg_type != MSGTYPE_CONNECT:
                  send_yate_msg(MSGTYPE_UNKNOWN_PEER,(),addr,self.sock)
            if self.handlers.has_key(msg_type):
               self.handlers[msg_type](msg_params,addr,msg_id)
         except Exception,e:
            yatelog.minor_exception('YATEServer','Error parsing packet from %s' % data)
   def read_packets(self):
       """ Do the minimal amount of work possible here and dispatch to a green thread for handling
       """
       while True:
         data,addr = self.sock.recvfrom(8192)
         self.in_q.put([data,addr])

if __name__=='__main__':
   logger = yatelog.get_logger()
   if len(sys.argv)==1:
      print 'Usage: yateserver [driver] [gameserver] [username] [password]'
      print '        <driver>      path to the driver module to use for this session'
      print '        [gameserver]  IP endpoint for the gameserver to connect to, passed to the driver - optional'
      print '        [username]    username to pass to the driver - optional'
      print '        [password]    password to pass to the driver - optional'
   elif len(sys.argv)>=2:
      logger.info('YATEServer: Trying to load driver: %s',sys.argv[1])
      try:
         drivermod = imp.load_source('yatedriver',sys.argv[1])
      except Exception,e:
         yatelog.fatal_exception('YATEServer','Could not load driver')
      logger.info('YATEServer: Loaded driver, starting server')
      try:
         server = YATEServer(drivermod.driver)
      except Exception,e:
         yatelog.fatal_exception('YATEServer','Could not start server')
      logger.info('YATEServer: Server running on port %s', server.get_port())
      while True: eventlet.greenthread.sleep(0)
