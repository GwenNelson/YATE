import eventlet
eventlet.monkey_patch()

import base

import zlib

import crypto
import packets
import buffer
import yatelog


protocol_modes = {
    0: 'init',
    1: 'status',
    2: 'login',
    3: 'play'
}

for k,v in protocol_modes.items(): protocol_modes[v] = k

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
       data = b""
       for arg in args:
           data += arg
       self.sock.sendraw(self.idents[self.sock.protocol_mode],data)

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
       self.compression_enabled = False
       
       self.cipher = crypto.Cipher()
       self.pool = eventlet.GreenPool(1000)
       
       self.recv_buff = buffer.Buffer()
       
       for k,v in packets.packet_idents.items():
           if k[0]==self.protocol_version:
              setattr(self,'send_%s' % k[3],MCSendMethod(k[3],self))

       self.pool.spawn_n(self.read_thread)
   def read_thread(self):
       while True:
          indata = self.tcp_sock.recv(1024)
          self.recv_buff.add(self.cipher.decrypt(indata))
          eventlet.greenthread.sleep(0)
          self.recv_buff.save()
          try:
             self.readpack()
          except buffer.BufferUnderrun:
             self.recv_buff.restore()
   def readpack(self):
       """ Reads a single packet from the socket
       """
       if self.protocol_mode < 3:
          max_bits = 21
       else:
          max_bits = 32
       packlen       = self.recv_buff.unpack_varint(max_bits=max_bits)
       self.recv_buff.add(self.cipher.decrypt(self.tcp_sock.recv(packlen)))
       packbody = self.recv_buff.read(packlen)
       pack_buff = buffer.Buffer()
       pack_buff.add(packbody)
       try:
          ident = pack_buff.unpack_varint()
          k     = (self.protocol_version,
                   protocol_modes[self.protocol_mode],
                   'downstream',
                    ident)
          yatelog.debug('MCSock','Trying to receive %s' % str(k))
       except:
          yatelog.minor_exception('MCSock','Failed decoding received packet')
   def sendraw(self,ident,data=b""):
       """ Used to send raw packets
            ident is the ID from packets.packet_idents
            data is the pre-serialised contents of the packet
       """
       rawpack = buffer.Buffer.pack_varint(ident) + data
       if self.compression_enabled: #TODO implement this
          pass

       if self.protocol_mode <3:
          max_bits = 21 # all modes but 'play'
       else:
          max_bits = 32 # 'play' mode

       # prepend length
       rawpack = buffer.Buffer.pack_varint(len(rawpack), max_bits=max_bits) + rawpack
       
       # encryption
       crypted_pack = self.cipher.encrypt(rawpack)
       self.tcp_sock.sendall(crypted_pack)
