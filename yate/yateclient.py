import eventlet
eventlet.monkey_patch()

import socket

from yateproto import *

class YATEClient:
   def __init__(self,server_addr=None):
       self.server_addr = server_addr
   def is_connected(self):
       if self.server_addr == None: return False
       return True
