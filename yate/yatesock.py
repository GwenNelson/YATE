import eventlet
eventlet.monkey_patch()

import gc
import socket
import msgpack

from yateproto import *

import yatelog

class YATESockSendMethod:
   def __init__(self,msg_type,sock):
       self.msg_type = msg_type
       self.sock     = sock
       self.q        = sock.out_queues[msg_type]
   def __call__(self,*args, **kwargs):
       to_addr = None
       if kwargs.has_key: to_addr = kwargs['to_addr']
       msg_id = gen_msg_id()
       self.q.put((args,msg_id,to_addr))
       return msg_id

class YATESocket:
   """ implements a UDP socket with message queues and async goodness and stuff
   """
   def __init__(self,bind_ip='127.0.0.1',bind_port=0,handlers={}):
       """ handlers is a dict mapping message type integers to functions that take the params (msg_params,msg_id,from_addr,sock)
       """
       self.sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
       self.sock.bind((bind_ip,bind_port))
       yatelog.info('YATESocket','Bound %s:%s' % self.sock.getsockname())
       yatelog.info('YATESocket','Setting up handlers and queues')
       self.pool = eventlet.GreenPool(1000)
       self.in_queues  = {}                             # packets coming in from remote peer go here after parsing, each message type has an independent queue so we can do QoS-type stuff
       self.out_queues = {}                             # packets going out to remote peer go here
       self.parse_q    = eventlet.queue.LightQueue(0)   # to keep up performance, packets go here before parsing
       self.handlers   = {MSGTYPE_CONNECT:self.handle_connect}
       self.handlers.update(handlers)
       self.active     = True
       for x in xrange(10): self.pool.spawn_n(self.parser_thread)
       for k,v in msgtype_str.items():
           self.in_queues[k]  = eventlet.queue.LightQueue(0)
           self.out_queues[k] = eventlet.queue.LightQueue(0)
           setattr(self,'send_%s' % v[8:].lower(),YATESockSendMethod(k,self)) # black magic
           for x in xrange(2): self.pool.spawn_n(self.msg_sender_thread,k)
           for x in xrange(2): self.pool.spawn_n(self.msg_reader_thread,k)
       self.known_peers = set() # if this is a server, this set contains the list of clients, if it's a client this contains only 1 member - the server
       self.pool.spawn_n(self.recv_thread)
   def get_endpoint(self):
       """ Return the IP endpoint this socket is bound to
       """
       return self.sock.getsockname()
   def msg_sender_thread(self, msg_type,delay=0):
       """ World's simplest QoS implementation is here - just set delay to the number of seconds to wait in between each packet transmission
       """
       msg_type_s = msgtype_str[msg_type]
       yatelog.debug('YATESock','Send thread for %s starting' % msg_type_s)
       while self.active:
          eventlet.greenthread.sleep(delay)
          msg_tuple = None
          while msg_tuple==None:
             eventlet.greenthread.sleep(0)
             try:
                msg_tuple = self.out_queues[msg_type].get()
             except:
                yatelog.minor_exception('YATESock','Error reading packet from queue')
          yatelog.debug('YATESocket','Got message to send, sending it now')
          if msg_tuple != None:
             msg_params = msg_tuple[0]
             msg_id     = msg_tuple[1]
             to_addr    = msg_tuple[2]
             msgdata    = msgpack.packb((msg_type,msg_params,msg_id))
             self.sock.sendto(msgdata,to_addr)
             yatelog.debug('YATESocket','Sent message %s to %s:%s' % (msg_type_s,to_addr[0],to_addr[1]))
   def handle_connect(self,msg_params,from_addr,msg_id):
       """ Handle new clients
       """
       self.known_peers.add(from_addr)
       self.send_connect_ack(msg_id,to_addr=from_addr)
   def msg_reader_thread(self, msg_type):
       """ This is used internally to handle all messages of the specified type when they come in from the parser thread
       """
       msg_type_s = msgtype_str[msg_type]
       yatelog.debug('YATESock','Receive thread for %s starting' % msg_type_s)
       while self.active:
          eventlet.greenthread.sleep(0)
          if not self.handlers.has_key(msg_type): # don't bother wasting CPU time on it, just pull from the queue and then do nothing else
             yatelog.warn('YATESock','No handler for %s' % msg_type_s)
             try:
                self.in_queues[msg_type].get()
             except:
                pass
             continue
          eventlet.greenthread.sleep(0)
          msg_tuple = None
          while msg_tuple==None:
             eventlet.greenthread.sleep(0)
             try:
                msg_tuple = self.in_queues[msg_type].get()
             except:
                yatelog.minor_exception('YATESock','Error reading packet from queue')
          if msg_tuple != None:
             msg_params = msg_tuple[0]
             msg_id     = msg_tuple[1]
             from_addr  = msg_tuple[2]
             if (from_addr in self.known_peers):
                self.handlers[msg_type](msg_params,from_addr,msg_id)
             else:
                if msg_type == MSGTYPE_CONNECT:
                   self.handle_connect(msg_params,from_addr,msg_id)
                else:
                   self.send_unknown_peer(to_addr=from_addr)
   def recv_thread(self):
       """ receives packets from the socket as fast as possible and shoves them into the parser queue
       """
       while self.active:
          eventlet.greenthread.sleep(0)
          data,addr = None,None
          try:
             data,addr = self.sock.recvfrom(8192)
          except:
             pass
          if data != None: self.parse_q.put((data,addr))

   def parser_thread(self):
       while self.active:
         eventlet.greenthread.sleep(0)
         data,addr = None,None
         while data==None:
            eventlet.greenthread.sleep(0)
            try:
               data,addr = self.parse_q.get()
            except:
               yatelog.minor_exception('YATESock','Failed during parse receive')
         if data != None:
            gc.disable() # performance hack for msgpack
            try:
               msg        = msgpack.unpackb(data,use_list = False)
               msg_type   = msg[0]
               msg_params = tuple(msg[1])
               msg_id     = msg[2]
               self.in_queues[msg_type].put((msg_params,msg_id,addr))
            except:
               yatelog.minor_exception('YATESocket','Error while parsing packet from %s:%s' % addr)
            gc.enable()
