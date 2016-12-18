import eventlet
eventlet.monkey_patch()

import base

import packets
import yatelog

protocol_modes = {
    0: 'init',
    1: 'status',
    2: 'login',
    3: 'play'
}

class MCSendMethod:
   def __init__(self,name,sock):
       yatelog.debug('MCSock','Adding new packet type: %s' % name)
       self.idents = {}
       self.name   = name
       self.sock   = sock
       for k,v in protocol_modes.items():
           if packets.packet_idents.has_key((sock.protocol_version,v,'upstream',name)):
              self.idents[k] = packets.packet_idents[(sock.protocol_version,v,'upstream',name)]
   def __call__(self,*args,**kwargs):
       if not self.idents.has_key(self.sock.protocol_mode):
          yatelog.warn('MCSock','No ident for packet in current protocol mode')
          return
       yatelog.debug('MCSock','Found valid ident for %s packet in protocol mode %s' % (self.name,protocol_modes[self.sock.protocol_mode]))

class MCSocket:
   """ This class represents a connection to a minecraft server
   """
   def __init__(self,endpoint,protocol_version=packets.default_protocol_version,protocol_mode=0):
       """ endpoint is a tuple of (ip,port)
           protocol_version
       """
       self.endpoint         = endpoint
       self.protocol_version = protocol_version
       self.protocol_mode    = protocol_mode
       self.tcp_sock = eventlet.connect(endpoint)
       
       for k,v in packets.packet_idents.items():
           if k[0]==self.protocol_version:
              setattr(self,'send_%s' % k[3],MCSendMethod(k[3],self))
           
   def sendraw(self,ident,data=b""):
       """ Used to send raw packets
            ident is the ID from packets.packet_idents
            data is the pre-serialised contents of the packet
       """
       pass
