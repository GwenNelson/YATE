import eventlet
eventlet.monkey_patch()
import base
import yatelog

from mcproto import mcsock
from mcproto import buffer

class MinecraftDriver(base.YateBaseDriver):
   def __init__(self,username=None,password=None,server='127.0.0.1:25565'):
       super(MinecraftDriver,self).__init__(username=username,password=password,server=server)
       self.username    = username
       self.password    = password
       self.avatar_uuid = None
       self.avatar_name = username # not always the same, just usually
       server_ip,server_port = server.split(':')
       self.server_addr = (server_ip,int(server_port))
       yatelog.info('minecraft','Minecraft driver starting up')
   
       pack_handlers = {'login_success':self.handle_login_success}

       self.sock = mcsock.MCSocket(self.server_addr,handlers=pack_handlers,display_name=username)
       self.sock.switch_mode(mcsock.protocol_modes['login'])
       while True:
          eventlet.greenthread.sleep(0)
   def handle_login_success(self,buff):
       self.avatar_uuid = buff.unpack_string()
       self.avatar_name = buff.unpack_string()
       self.sock.switch_mode("play")
       yatelog.info('minecraft','Connected to minecraft server %s:%s with display name "%s" and avatar UUID %s' % (self.server_addr[0],self.server_addr[1],self.avatar_name,self.avatar_uuid))

driver = MinecraftDriver
