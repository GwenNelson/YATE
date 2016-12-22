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
       if not kwargs.has_key('protomode'):
          protomode = self.sock.protocol_mode
       else:
          protomode = kwargs['protomode']
       if not self.idents.has_key(protomode):
          yatelog.warn('MCSock','No ident for packet %s in current protocol mode %s' % (self.name,protocol_modes[protomode]))
          return
       data = b""
       for arg in args:
           data += arg
       self.sock.sendraw(self.idents[protomode],data)

class MCSocket:
   """ This class represents a connection to a minecraft server
   """
   def __init__(self,endpoint=None,protocol_version=packets.default_protocol_version,protocol_mode=0,handlers={},display_name='YATEBot'):
       """ endpoint is a tuple of (ip,port) or None - if None, use connect_to() later
           protocol_version is the version of the minecraft protocol to use
           protocol_mode should be 0 at start, but if you're a psycho you can of course set it to ANYTHING you want - think of the possibilities
           handlers maps packet names to handlers that accept the packet data - it's up to the handler to decode the packet at present
           display_name is what it sounds like
           despite this thing being in eventlet, it's pretty much blocking - because notch owes me now, also it's a TCP socket and there's probably ordering issues
       """
       self.endpoint              = endpoint
       self.protocol_version      = protocol_version
       self.protocol_mode         = protocol_mode
       self.display_name          = display_name
       self.compression_threshold = 0
       self.compression_enabled   = False

       self.handlers = {'login_set_compression':self.handle_login_set_compression,
                        'keep_alive':           self.handle_keep_alive,
                        'set_compression':      self.handle_set_compression}
       self.handlers.update(handlers)
       self.cipher   = crypto.Cipher()
       self.pool     = eventlet.GreenPool(1000)
       
       self.ready             = False
       self.blocking_handlers = False # if set to True, packet handlers will be invoked by the reader thread

       for k,v in packets.packet_idents.items():
           if k[0]==self.protocol_version:
              setattr(self,'send_%s' % k[3],MCSendMethod(k[3],self))
       if endpoint != None:
          self.connect_to(endpoint)
   def set_compression(self,threshold):
       """ Used internally for compression packet handlers
       """
       if not self.compression_enabled:
          self.compression_enabled = True
          yatelog.debug('MCSock','Compression enabled')
       self.compression_threshold = threshold
   def handle_keep_alive(self,buff):
       keep_alive_id = buff.unpack_varint()
       self.send_keep_alive(buffer.Buffer.pack_varint(keep_alive_id))
   def handle_login_set_compression(self,buff):
       new_threshold = buff.unpack_varint()
       self.set_compression(new_threshold)
   def handle_set_compression(self,buff):
       new_threshold = buff.unpack_varint()
       self.set_compression(new_threshold)
   def switch_mode(self,new_mode=protocol_modes['login']):
       """ Use this to switch protocol mode after a connection is established
           new_mode is the integer describing the new mode to switch to (default is login)
           status is not supported because YATE has no use for it
       """
       if not(type(new_mode) is int): new_mode = protocol_modes[new_mode]
       yatelog.info('MCSock','Switching protocol modes: %s to %s' % (protocol_modes[self.protocol_mode], protocol_modes[new_mode]))
       oldmode = self.protocol_mode
       self.protocol_mode = new_mode
       if new_mode==protocol_modes['login']:
          self.send_handshake(buffer.Buffer.pack_varint(self.protocol_version),
                              buffer.Buffer.pack_string(self.endpoint[0]),
                              buffer.Buffer.pack('H',self.endpoint[1]),
                              buffer.Buffer.pack_varint(protocol_modes['login']),protomode=oldmode)
       
       if self.protocol_mode == protocol_modes['login']:
          self.send_login_start(buffer.Buffer.pack_string(self.display_name))


   def connect_to(self,endpoint):
       """ Use this to connect to the server if an endpoint is not passed in __init__
       """
       self.tcp_sock            = eventlet.connect(endpoint)
       self.cipher              = crypto.Cipher()
       self.recv_buff           = buffer.Buffer()
       self.compression_enabled = False
       self.protocol_mode       = 0 # did you really think it made sense to set this to anything else you maniac?
       self.send_q              = eventlet.queue.LightQueue(0)
       self.ready               = True
       self.pool.spawn_n(self.read_thread)
       self.pool.spawn_n(self.send_thread)
   def send_thread(self):
       while True:
          outdata = self.send_q.get()
          eventlet.greenthread.sleep(0)
          try:
             self.tcp_sock.sendall(outdata)
          except:
             yatelog.fatal_exception('MCSock','Could not transmit to the server')

   def handler_wrapper(self,name,handler,buff):
       """ A wrapper for doing async handlers while still tracking exceptions in yatelog
       """
       try:
          handler(buff)
       except:
          yatelog.minor_exception('MCSock','Error running handler for %s' % name)
   def read_thread(self):
       while True:
          indata = self.tcp_sock.recv(1024)
          self.recv_buff.add(self.cipher.decrypt(indata))
          eventlet.greenthread.sleep(0)
          self.recv_buff.save()
          try:
             self.readpack()
             eventlet.greenthread.sleep(0)
          except buffer.BufferUnderrun:
             self.recv_buff.restore()
   def readpack(self):
       """ Reads a single packet from the socket
           Used internally, must NOT be called from anywhere but read_thread lest bad things happen
           After reading the packet, if a handler is registered then we throw it to that handler in a greenlet
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
       if self.compression_enabled:
          uncompressed_len = pack_buff.unpack_varint()
          if uncompressed_len > 0:
             data = zlib.decompress(pack_buff.read())
             pack_buff = buffer.Buffer()
             pack_buff.add(data)
       try:
          ident = pack_buff.unpack_varint()
          k     = (self.protocol_version,
                   protocol_modes[self.protocol_mode],
                   'downstream',
                    ident)
          if packets.packet_names.has_key(k):
             if self.handlers.has_key(packets.packet_names[k]):
                try:
                   if self.blocking_handlers:
                     self.handlers[packets.packet_names[k]](pack_buff)
                   else:
                     self.pool.spawn_n(self.handler_wrapper,packets.packet_names[k],self.handlers[packets.packet_names[k]],pack_buff)
                except:
                   yatelog.minor_exception('MCSock','Error scheduling packet handler')
             else:
                yatelog.warn('MCSock','Received unhandled packet: %s' % packets.packet_names[k])
          else:
             yatelog.error('MCSock','Unknown packet received: %s' % str(k))
       except:
          yatelog.minor_exception('MCSock','Failed decoding received packet')
   def sendraw(self,ident,data=b""):
       """ Used to send raw packets
            ident is the ID from packets.packet_idents
            data is the pre-serialised contents of the packet
           To avoid race conditions, the actual transmission takes place in send_thread - which makes it possible to sprinkle a few sleeps in here and boost performance mildly
       """
       rawpack = buffer.Buffer.pack_varint(ident) + data
       if self.compression_enabled:
          if len(rawpack) >= self.compression_threshold:
             rawpack = buffer.Buffer.pack_varint(len(rawpack)) + zlib_compress(rawpack)
          else:
             rawpack = buffer.Buffer.pack_varint(0) + rawpack

       eventlet.greenthread.sleep(0)

       if self.protocol_mode <3:
          max_bits = 21 # all modes but 'play'
       else:
          max_bits = 32 # 'play' mode

       # prepend length
       rawpack = buffer.Buffer.pack_varint(len(rawpack), max_bits=max_bits) + rawpack
       
       eventlet.greenthread.sleep(0)
       
       # encryption
       crypted_pack = self.cipher.encrypt(rawpack)
       self.send_q.put(crypted_pack)
