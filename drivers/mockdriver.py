class MockDriver:
   def __init__(self):
       pass
   def get_msg_handlers(self):
       """ Return a dictionary of message types mapped to message handlers that the driver wants to deal with directly
       """
       return {}

driver = MockDriver()
