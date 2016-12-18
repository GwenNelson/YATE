""" This file is an example driver for implementing other games
    It implements a static 2D environment with walls around the edges and some obstacles in the middle to test pathfinding
    Visual range is set to the size of the whole map, which is a bit of a cheat
    The map is surrounded by a void of unknown voxels
    Turning this thing into a raycaster maze that runs on its own would not be too difficult
"""
import base # always import this cos it allows us to do the below imports

import yatelog
from yateproto import *

mock_environment = """
777777777777777777777777777
771111111111111111111111177
771001000000003000000000177
771001011111111411111111177
771001010000001000000000177
771001010000001000000000177
771001010000001000000000177
771001010000000000000000177
77100121111110000A000000177
771000000000000000000000177
771111111111111111111111177
777777777777777777777777777
"""


class MockDriver(base.YateBaseDriver):
   def __init__(self,username=None,password=None,server=None):
       super(MockDriver,self).__init__(username=username,password=password,server=server)
       self.username    = username
       self.password    = password
       self.server_addr = server
       self.setup_env()
   def setup_env(self):
       self.env = {}
       x = 0
       y = 0
       z = 0
       for line in mock_environment.split('\n'):
           if len(line)>4:
              x  = 0
              for c in line:
                  if c=='A':
                     self.spatial_pos = (x,y,z)
                     b_type = 0
                  else:
                     b_type = int(c)
                  self.env[(x,y,z)] = base.YateBaseVoxel(spatial_pos=(x,y,z),basic_type=b_type)
                  x += 1
           y += 1
       self.visual_range = (x/2,y/2,2)

   def get_pos(self):
       return self.spatial_pos
   def move_vector(self,vector):
       """ This function squashes the vector into 2D space, scales it so it only moves 1 voxel at a time and
           finally moves in the relevant direction if possible
       """
       cur_x,cur_y,cur_z = self.get_pos()
       vec_x,vec_y,vec_z = int(vector[0]),int(vector[1]),int(vector[2])
       if vec_x > 0: vec_x = 1
       if vec_y > 0: vec_y = 1
       if vec_x < 0: vec_x = -1
       if vec_y < 0: vec_y = -1
       new_x = cur_x + vec_x
       new_y = cur_y + vec_y
       new_z = cur_z
       new_vox = self.get_voxel((new_x,new_y,new_z))
       vox_pos = new_vox.get_pos()
       if new_vox.can_traverse():
          if new_vox.can_destroy():
             self.destroy_voxel(vox_pos)
          else:
             if new_vox.can_open():
                if not new_vox.is_open(): self.interact_voxel(vox_pos)
          self.spatial_pos = (new_x,new_y,new_z)
   def get_vision_range(self):
       return self.visual_range
   def destroy_voxel(self,voxel_pos):
       old_vox = self.get_voxel(voxel_pos)
       if not old_vox.can_destroy(): return
       new_vox = base.YateBaseVoxel(spatial_pos=voxel_pos,basic_type=YATE_VOXEL_EMPTY)
       self.env[voxel_pos] = new_vox
   def interact_voxel(self,voxel_pos):
       old_vox = self.get_voxel(voxel_pos)
       if not old_vox.can_open(): return
       if old_vox.active_state == YATE_VOXEL_ACTIVE:
          new_vox = base.YateBaseVoxel(spatial_pos=voxel_pos,basic_type=old_vox.basic_type,specific_type=old_vox.specific_type,active_state=YATE_VOXEL_INACTIVE)
       elif old_vox.active_state == YATE_VOXEL_INACTIVE:
          new_vox = base.YateBaseVoxel(spatial_pos=voxel_pos,basic_type=old_vox.basic_type,specific_type=old_vox.specific_type,active_state=YATE_VOXEL_ACTIVE)
       self.env[voxel_pos] = new_vox

   def get_voxel(self,voxel_pos):
       if self.env.has_key(voxel_pos):
          return self.env[voxel_pos]
       else:
          return base.YateBaseVoxel(spatial_pos=voxel_pos,basic_type=YATE_VOXEL_UNKNOWN) # if outside of the map, the unknown void wherein Azathoth lurks (or something)

driver = MockDriver()
