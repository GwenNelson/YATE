""" This file is an example driver for implementing other games
    It implements a static 2D environment with walls around the edges and some obstacles in the middle to test pathfinding
    Visual range is set to the size of the whole map, which is a bit of a cheat
    The map is surrounded by a void of unknown voxels
    Turning this thing into a raycaster maze that runs on its own would not be too difficult
"""
import base

mock_environment = """
77777777777777777777777777777777
77711111111111111111111111777777
77710010000000030000000001777777
77710010111111114111111111777777
77710010100000010000000001777777
77710010100000010000000001777777
77710010100000010000000001777777
77710010100000000000000001777777
777100121111110000A0000001777777
77710000000000000000000001777777
77711111111111111111111111777777
77777777777777777777777777777777
77777777777777777777777777777777
"""

def create_env():
    """ Create a hashmap of the mock environment and return it along with avatar coordinates and visual range
        Return format is a tuple (env,avatar_pos,visual_range)
    """
    env = {}
    x = 0
    y = 0
    z = 0 # because it's 2D, everything is on a single plane
    avatar_pos = None
    for line in mock_environment.split('\n'):
        x += 1
        for c in line:
            y += 1
            if c=='A':
               avatar_pos = (x,y,z)
               b_type = 0
            else:
               b_type = int(str(c))
            env[(x,y,z)] = base.YateBaseVoxel(spatial_pos=(x,y,z),basic_type=b_type)
    return (env,avatar_pos,(x,y,1))

class MockDriver(base.YateBaseDriver):
   def __init__(self,username=None,password=None,server=None):
       self.username    = username
       self.password    = password
       self.server_addr = server
       env,avatar_pos,visual_range = create_env()
       self.env          = env
       self.spatial_pos  = avatar_pos
       self.visual_range = visual_range
   def get_mypos(self):
       return self.spatial_pos
   def move_vector(self,vector):
       """ This function squashes the vector into 2D space, scales it so it only moves 1 voxel at a time and
           finally moves in the relevant direction if possible
       """
       cur_x,cur_y,cur_z = self.get_mypos()
       vec_x,vec_y,vec_z = int(vector[0]),int(vector[1]),int(vector[2])
       if vec_x > 0: vec_x = 1
       if vec_y > 0: vec_y = 1
       if vec_x < 0: vec_x = -1
       if vec_y < 0: vec_y = -1
       new_x = cur_x + vec_x
       new_y = cur_y + vec_y
       new_z = cur_z
       new_vox = self.get_voxel((new_x,new_y,new_z))
       if new_vox.can_traverse():
          if new_vox.can_destroy():
             self.destroy_voxel(new_vox)
          else:
             if new_vox.can_open():
                self.interact_voxel(new_vox)
          self.spatial_pos = new_vox

   def get_voxel(self,spatial_pos):
       return self.env[tuple(spatial_pos)]

driver = MockDriver()
