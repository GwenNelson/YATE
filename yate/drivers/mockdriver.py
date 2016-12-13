""" This file is an example driver for implementing other games
"""
import random
import yateproto

class MockPercept:
""" since this is a mock percept, it chooses what to be at random
"""
   def __init__(self):
       self.type


class MockDriver:
   def __init__(self):
       pass
   def get_msg_handlers(self):
       """ Return a dictionary of message types mapped to message handlers that the driver wants to deal with directly
       """
       return {}
   def percept_stream(self):
       """ Yield a stream of percepts
       """
       while True:
          yield MockPercept()

driver = MockDriver()
