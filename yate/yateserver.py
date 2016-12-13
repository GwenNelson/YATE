import eventlet
eventlet.monkey_patch()
import sys
import yatelog
import imp
import socket
import msgpack

class YATEServer:
   def __init__(self,driver):
       self.logger = yatelog.get_logger()
       self.driver = driver
       self.sock   = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
       self.pool   = eventlet.GreenPool()
       self.in_q   = eventlet.queue.LightQueue()
       self.sock.bind(('127.0.0.1',0))
       self.pool.spawn_n(self.read_packets)
       for x in xrange(10): self.pool.spawn_n(self.proc_packets)
   def get_port(self):
       return self.sock.getsockname()[1]
   def proc_packets(self):
       while True:
         data,addr = self.in_q.get(block=True)
         try:
            parsed_data = msgpack.unpackb(data)
         except Exception,e:
            logger.minor_exception('YATEServer','Error parsing packet from %s' % data)
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
