""" This file contains constants and other stuff useful for dealing with the YATE network protocol
    Please note that this protocol does not take security into consideration AT ALL, everything should run on localhost only
"""
import msgpack
import random
import time
import hashlib

# basic voxel types - "easy to destroy" means YATE can do it automatically, "with effort" means the AI must send the command
YATE_VOXEL_EMPTY             = 0 # air or empty space
YATE_VOXEL_TOTAL_OBSTACLE    = 1 # total obstacle: can not traverse OR destroy
YATE_VOXEL_EASY_OBSTACLE     = 2 # traversible only after destroying, easy to destroy
YATE_VOXEL_DOOR_OBSTACLE     = 3 # traversible after interaction but not destroyable - intended for doors and such which can never be destroyed
YATE_VOXEL_DOOR_EASY_DESTROY = 4 # traversible after interaction but also destroyable easily
YATE_VOXEL_DOOR_HARD_DESTROY = 5 # traversible after interaction and destroyable, but only with effort - use this for minecraft-type doors
YATE_VOXEL_HARD_OBSTACLE     = 6 # traversible and destroyable, but only with effort
YATE_VOXEL_UNKNOWN           = 7 # we don't know anything about this voxel

# interactible state
YATE_VOXEL_INACTIVE = 0 # switch is off, door is closed, etc
YATE_VOXEL_ACTIVE   = 1 # switch is on, door is open, etc

# destroyable state - it is assumed that when destroyed voxels are replaced with a different type, so there is no destroyed state
YATE_VOXEL_INTACT      = 0 # totally intact, no effort has been made to destroy
YATE_VOXEL_PART_INTACT = 1 # partly intact, some effort has been made to destroy

# params for each message type are shown below
MSGTYPE_CONNECT       = 0 # ()
MSGTYPE_CONNECT_ACK   = 1 # (msg_id) msg_id is the msg_id from the original keepalive packet
MSGTYPE_UNKNOWN_PEER  = 2 # () signals to the other peer that we don't know who they are
MSGTYPE_KEEPALIVE     = 3 # ()
MSGTYPE_KEEPALIVE_ACK = 4 # (msg_id) msg_id is the msg_id from the original keepalive packet

YATE_KEEPALIVE_TIMEOUT = 2 # in seconds

# for performance reasons, the below is used instead of strings for keys in the clients dictionary in yateserver.py
YATE_LAST_ACKED = 0 # a set of message IDs from incoming ACK packets - we use a set cos UDP can be weird
YATE_SOCK_ADDR  = 1

def gen_msg_id():
    """ Generate a random-ish message ID integer and return it
        This is NOT cryptographically secure, it's just meant to be unique enough not to clash
    """
    return int(hashlib.sha256(str(time.time()+random.randint(1,9999))).hexdigest()[:6],16)

def send_yate_msg(msgtype,params,addr,sock):
    """ Sends a message and returns the message ID
    """
    msgid   = gen_msg_id()
    msgdata = msgpack.packb((msgtype,params,msgid))
    sock.sendto(msgdata,(addr[0],addr[1]))
    return msgid
