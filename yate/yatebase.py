class YateBaseGame:
""" This class is the base representing a game
    At time of writing the only supported game in YATE is minecraft, so that is the only class inheriting from this one
"""
   def __init__(self,username,password,server):
       """ When overriding, the constructor should setup the connection and get into a state where the game is playable
           by the AI's avatar - the username,password and server params are self explanatory and may optionally be ignored
           if doing so is appropriate. If the setup fails, then the constructor should throw an exception
       """
       pass
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
