import base

import yatelog

class MinecraftDriver(base.YateBaseDriver):
   def __init__(self,username=None,password=None,server=None):
       super(MinecraftDriver,self).__init__(username=username,password=password,server=server)
       self.username    = username
       self.password    = password
       self.server_addr = server
       yatelog.info('minecraft','Minecraft driver starting up')

driver = MinecraftDriver
