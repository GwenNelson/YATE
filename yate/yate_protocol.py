import zlib
import msgpack

from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor

class YATE(DatagramProtocol):
   def startProtocol(self):
       self.known_peers = set()
