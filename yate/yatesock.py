import eventlet
eventlet.monkey_patch()

import gc
import socket
import msgpack

from yateproto import *

import yatelog
import time

class YATESockSendMethod:
   def __init__(self,msg_type,sock):
       self.msg_type = msg_type
       self.sock     = sock
       self.q        = sock.out_queues[msg_type]
   def __call__(self,*args, **kwargs):
       to_addr = None
       if kwargs.has_key('to_addr'): to_addr = kwargs['to_addr']
       msg_id = gen_msg_id()
       self.q.put((args,msg_id,to_addr))
       return msg_id

class YATESocket:
   """ implements a UDP socket with message queues and async goodness and stuff
   """
   def __init__(self,bind_ip='127.0.0.1',bind_port=0,handlers={},enable_null_handle=True):
       """ handlers is a dict mapping message type integers to functions that take the params (msg_params,msg_id,from_addr,sock)
           enable_null_handle enables a default "null handler" that does nothing with unhandled message types except logging them to debug
       """
       self.sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
       self.sock.bind((bind_ip,bind_port))
       yatelog.info('YATESock','Bound %s:%s' % self.sock.getsockname())
       yatelog.info('YATESock','Setting up handlers and queues')
       self.pool = eventlet.GreenPool(1000)
       self.in_queues  = {}                             # packets coming in from remote peer go here after parsing, each message type has an independent queue so we can do QoS-type stuff
       self.out_queues = {}                             # packets going out to remote peer go here
       self.parse_q    = eventlet.queue.LightQueue(0)   # to keep up performance, packets go here before parsing
       self.handlers   = {MSGTYPE_CONNECT:      self.handle_connect,       # a couple of standard message handlers, override by passing in new handlers
                          MSGTYPE_UNKNOWN_PEER: self.handle_unknown_peer,
                          MSGTYPE_CONNECT_ACK:  self.handle_connect_ack,
                          MSGTYPE_KEEPALIVE:    self.handle_keepalive,
                          MSGTYPE_KEEPALIVE_ACK:self.handle_keepalive_ack}
       self.handlers.update(handlers)
       self.enable_null_handle = enable_null_handle
       self.active     = True

       for x in xrange(10): self.pool.spawn_n(self.parser_thread)
       for k,v in msgtype_str.items():
           self.in_queues[k]  = eventlet.queue.LightQueue(0)
           self.out_queues[k] = eventlet.queue.LightQueue(0)
           setattr(self,'send_%s' % v[8:].lower(),YATESockSendMethod(k,self)) # black magic
           for x in xrange(2): self.pool.spawn_n(self.msg_sender_thread,k)
           for x in xrange(2): self.pool.spawn_n(self.msg_reader_thread,k)
           if enable_null_handle:
              if not self.handlers.has_key(k): self.handlers[k] = self.null_handler
       self.known_peers = set() # if this is a server, this set contains the list of clients, if it's a client this contains only 1 member - the server
       self.last_pack   = {}    # store the timestamp of the last packet from a particular peer so we can do timeouts
       self.pool.spawn_n(self.recv_thread)
       self.pool.spawn_n(self.timeout_thread) # timeout peers all in a central location, giving plenty of time for them to send packets and not timeout
   def stop(self):
       """ terminate threads and close cleanly
       """
       self.active = False
       self.pool.waitall()
       self.sock.shutdown()
   def connect_to(self,addr):
       """ Connect to the specified remote peer - this pretty much only really makes sense for clients
       """
       yatelog.info('YATESock','Connecting to peer at %s:%s' % addr)
       msg_id = self.send_connect(to_addr=addr)
       self.handle_connect(tuple(),addr,msg_id)
   def is_connected(self,addr):
       """ Query if the specified peer is still connected
       """
       return (addr in self.known_peers)
   def get_endpoint(self):
       """ Return the IP endpoint this socket is bound to
       """
       return self.sock.getsockname()
   def msg_sender_thread(self, msg_type,delay=0):
       """ World's simplest QoS implementation is here - just set delay to the number of seconds to wait in between each packet transmission
       """
       msg_type_s = msgtype_str[msg_type]
       while self.active:
          eventlet.greenthread.sleep(delay)
          msg_tuple = None
          while msg_tuple==None:
             eventlet.greenthread.sleep(0)
             try:
                msg_tuple = self.out_queues[msg_type].get()
             except:
                yatelog.minor_exception('YATESock','Error reading packet from queue')
          if msg_tuple != None:
             msg_params = msg_tuple[0]
             msg_id     = msg_tuple[1]
             to_addr    = msg_tuple[2]
             msgdata    = msgpack.packb((msg_type,msg_params,msg_id))
             if to_addr==None:
                yatelog.debug('YATESock','Broadcasting message %s to all peers: %s' % (msg_type,msg_params))
                peer_list = self.known_peers.copy()
                for peer in peer_list:
                    try:
                       self.sock.sendto(msgdata,peer)
                       yatelog.debug('YATESock','Sent broadcast message to %s:%s' % peer)
                    except:
                       yatelog.minor_exception('YATESock','Error during broadcast of message')
             else:
                try:
                   self.sock.sendto(msgdata,to_addr)
                   yatelog.debug('YATESock','Sent message %s to %s:%s: %s' % (msg_type_s,to_addr[0],to_addr[1],msg_params))
                except:
                   yatelog.minor_exception('YATESock','Error during transmission of message')
                    
   def null_handler(self,msg_params,from_addr,msg_id):
       """ null handler - just dumps the message to log
       """
       yatelog.info('YATESock','Null handler dump: message ID %s from %s:%s: %s' % (msg_id,from_addr[0],from_addr[1],str(msg_params)))
   def handle_unknown_peer(self,msg_params,from_addr,msg_id):
       """ Handle the UNKNOWN_PEER message
       """
       self.known_peers.discard(from_addr)
       yatelog.info('YATESock','Peer %s:%s does not know us, perhaps we timed out?' % from_addr)
   def handle_connect_ack(self,msg_params,from_addr,msg_id):
       """ Confirmed new peers - only really here to shutup the warning when not overridden
       """
       yatelog.debug('YATESock','Confirmed connection to %s:%s' % from_addr)
   def handle_connect(self,msg_params,from_addr,msg_id):
       """ Handle new peers - this is also called when we connect outwards, so don't subclass and override it like a fool
       """
       self.known_peers.add(from_addr)
       self.pool.spawn_n(self.do_keepalive,from_addr) # send packets to this peer on a regular basis
       self.send_connect_ack(msg_id,to_addr=from_addr)
   def timeout_thread(self):
       """ kill peers that have timed out
       """
       while self.active:
          eventlet.greenthread.sleep(YATE_KEEPALIVE_TIMEOUT)
          cur_time  = time.time()
          peer_list = self.known_peers.copy() # thread safety bitches
          for peer in peer_list:
              if not self.last_pack.has_key(peer):
                 yatelog.warn('YATESock','Peer %s:%s never actually sent us a single packet after connecting' % peer)
                 self.known_peers.discard(peer)
              if cur_time - self.last_pack[peer] > YATE_KEEPALIVE_TIMEOUT:
                 yatelog.info('YATESock','Peer %s:%s has timed out, bye' % peer)
                 self.known_peers.discard(peer)
   def do_keepalive(self,client_addr):
       """ send keepalive packets to the peer so we don't time out
       """
       while self.active and (client_addr in self.known_peers):
          eventlet.greenthread.sleep(YATE_KEEPALIVE_TIMEOUT/2)
          if client_addr in self.known_peers: self.send_keepalive(to_addr=client_addr)
   def handle_keepalive(self,msg_params,from_addr,msg_id):
       """ Send back KEEPALIVE_ACK so we don't time out
       """
       self.send_keepalive_ack(msg_id,to_addr=from_addr)
   def handle_keepalive_ack(self,msg_params,from_addr,msg_id):
       """ Do nothing, absolutely nothing, fuck all, zilch, zero - the receive loop tracks stuff for us
       """
       pass
   def msg_reader_thread(self, msg_type):
       """ This is used internally to handle all messages of the specified type when they come in from the parser thread
       """
       msg_type_s = msgtype_str[msg_type]
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
             yatelog.debug('YATESock','Got message %s from %s:%s: %s' % (msg_type_s,from_addr[0],from_addr[1],msg_params))
             if (from_addr in self.known_peers):
                try:
                   self.handlers[msg_type](msg_params,from_addr,msg_id)
                except:
                   yatelog.minor_exception('YATESock','Error handling message')
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
          if data != None:
             # store the actual time we got the packet here, it's not fair to timeout peers for our slow parsing
             if addr in self.known_peers: # but don't open up a very silly DDoS vulnerability
                self.last_pack[addr] = time.time()
             self.parse_q.put((data,addr))

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
               msg_params = msg[1]
               msg_id     = msg[2]
               self.in_queues[msg_type].put((msg_params,msg_id,addr))
            except:
               yatelog.minor_exception('YATESock','Error while parsing packet from %s:%s' % addr)
            gc.enable()
