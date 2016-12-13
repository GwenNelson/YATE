""" This file is an example driver for implementing other games
"""
import base

class MockDriver(base.YateBaseDriver):
   def __init__(self,username=None,password=None,server=None):
       self.username    = username
       self.password    = password
       self.server_addr = server
       self.spatial_pos = (64,64,64)
   def get_mypos(self):
       return self.spatial_pos
   def walk_to_space(self,x,y,z):
       self.spatial_pos = (x,y,z)

driver = MockDriver()
