""" This file contains constants and other stuff useful for dealing with the YATE network protocol
    Please note that this protocol does not take security into consideration AT ALL, everything should run on localhost only
"""
import eventlet
eventlet.monkey_patch()
import msgpack
import random

# params for each message type are shown below
MSGTYPE_CONNECT       = 0 # ()
MSGTYPE_CONNECT_ACK   = 1 # (msg_id) msg_id is the msg_id from the original keepalive packet
MSGTYPE_UNKNOWN_PEER  = 2 # () signals to the other peer that we don't know who they are
MSGTYPE_KEEPALIVE     = 3 # ()
MSGTYPE_KEEPALIVE_ACK = 4 # (msg_id) msg_id is the msg_id from the original keepalive packet

YATE_KEEPALIVE_TIMEOUT = 2 # in seconds

# for performance reasons, the below is used instead of strings for keys in the clients dictionary in yateserver.py
YATE_LAST_ACKED = 0 # a set of message IDs from incoming ACK packets - we use a set cos UDP can be weird

def gen_msg_id():
    """ Generate a random-ish message ID integer and return it
        This is NOT cryptographically secure, it's just meant to be unique enough not to clash
    """
    return int(hashlib.sha256(str(time.time()+random.randint(1,9999))).hexdigest()[:6],16)

def send_yate_msg(msgtype,params,addr,sock):
    """ Sends a message and returns the message ID
    """
    msgid   = gen_msg_id()
    msgdata = msgpack.packb((msgtype,params))
    sock.sendto(msgdata,addr)
    return msgid
