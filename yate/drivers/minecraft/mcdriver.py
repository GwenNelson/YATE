import eventlet
eventlet.monkey_patch()
import base
import yatelog

from mcproto import mcsock

class MinecraftDriver(base.YateBaseDriver):
   def __init__(self,username=None,password=None,server='127.0.0.1:25565'):
       super(MinecraftDriver,self).__init__(username=username,password=password,server=server)
       self.username    = username
       self.password    = password
       server_ip,server_port = server.split(':')
       self.server_addr = (server_ip,int(server_port))
       yatelog.info('minecraft','Minecraft driver starting up')
       self.sock = mcsock.MCSocket(self.server_addr)

driver = MinecraftDriver
