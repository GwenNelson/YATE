from .. import yatelog
from .. import yateproto
from yateproto import *

class YateBaseVoxel:
""" This class may either be used directly or inherited from and extended for game-specific mechanics etc
"""
   def __init__(self,spatial_pos=(64,64,64),basic_type=YATE_VOXEL_EMPTY,specific_type=0):
       """ spatial_pos   is obvious
           basic_type    is the basic voxel type as defined in yateproto.py
           specific_type is optional and specifies the game-specific extended type
       """
       self.spatial_pos   = spatial_pos
       self.basic_type    = basic_type
       self.specific_type = specific_type

   def can_traverse(self, no_destroy=False, no_interact=False):
       """ return a boolean value indicating whether or not this voxel can be traversed by YATE automatically during pathfinding
           if no_destroy is set to True, we assume that YATE_VOXEL_EASY_OBSTACLE will not be destroyed
           if no_interact is set to True, we assume that YATE_VOXEL_DOOR_OBSTACLE will not be interacted with
           if the voxel basic type is unknown, we assume it can NOT be traversed until proven otherwise
           this method will also throw an exception if self.basic_type is not a proper basic type
       """
       return {YATE_VOXEL_EMPTY:             True,
               YATE_VOXEL_TOTAL_OBSTACLE:    False,
               YATE_VOXEL_EASY_OBSTACLE:     not no_destroy,
               YATE_VOXEL_DOOR_OBSTACLE:     not no_interact,
               YATE_VOXEL_DOOR_EASY_DESTROY: (not no_destroy) or (not no_interact),
               YATE_VOXEL_DOOR_HARD_DESTROY: not no_interact,
               YATE_VOXEL_HARD_OBSTACLE:     False,
               YATE_VOXEL_UNKNOWN:           False}[self.basic_type]
   
   def can_destroy(self):
       """ return a boolean value indicating whether or not this voxel can be destroyed by YATE automatically during pathfinding
           if the voxel can only be destroyed with effort, this will return False
       """
       return {YATE_VOXEL_EMPTY:             False,
               YATE_VOXEL_TOTAL_OBSTACLE:    False,
               YATE_VOXEL_EASY_OBSTACLE:     True,
               YATE_VOXEL_DOOR_OBSTACLE:     False, # doors should never be destroyed automatically
               YATE_VOXEL_DOOR_EASY_DESTROY: False,
               YATE_VOXEL_DOOR_HARD_DESTROY: False,
               YATE_VOXEL_HARD_OBSTACLE:     False,
               YATE_VOXEL_UNKNOWN:           False}[self.basic_type]
 
class YateBaseDriver:
""" This class is the base used for all drivers
    At time of writing the only supported game in YATE is minecraft, so that is the only class inheriting from this one
"""
   def __init__(self,username=None,password=None,server=None):
       """ When overriding, the constructor should setup the connection and get into a state where the game is playable
           by the AI's avatar - the username,password and server params are self explanatory and may optionally be ignored
           if doing so is appropriate. If the setup fails, then the constructor should throw an exception
       """
       pass
   def get_msg_handlers(self):
       """ Return a dictionary of message types mapped to message handlers that the driver wants to deal with directly
       """
       return {}
   def respawn(self):
       """ If the AI's avatar is dead, respawn if possible - if respawning requires a particular amount of time
           this method should block. If the AI's avatar is alive and it is possible to do so, this method should
           force a respawn
       """
       pass
   def tick(self):
       """ This method will be called in a loop by YATE, if the game requires regular activity of any kind it should go here.
           If the game requires particular timing for things such as keepalive packets it should be tracked here.
           This method should NOT block using time.sleep or similar
       """
       pass
   def get_mypos(self):
       """ This method should return a tuple representing coordinates in 3D space of the AI's avatar
       """
       pass
   def walk_to_space(self,x,y,z):
       """ This method should attempt to walk to the specified space with an appropriate pathfinding algorithm
           Failed attempts are acceptable as this method is intended as a primitive for higher-level algorithms on the AI side
       """
       pass
   def get_voxel(self,x,y,z):
       """ This method should return a voxel object describing the specified 3D coordinates. If the AI's avatar can not
           see the coordinates this method should return None
       """
       pass
   def get_voxel_strings(self):
       """ This method should return a dict that maps voxel type integers to strings
       """
       pass
   def get_entity_strings(self):
       """ This method should return a dict that maps entity type integers to strings
       """
       pass
   def get_item_strings(self):
       """ This method should return a dict that maps item type integers to strings
       """
       pass
