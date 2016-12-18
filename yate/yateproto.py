""" This file contains constants and other stuff useful for dealing with the YATE network protocol
    Please note that this protocol does not take security into consideration AT ALL, everything should run on localhost only
"""
import msgpack
import random
import time
import hashlib
import sys
import yatelog

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

# perception related messages
MSGTYPE_REQUEST_VISUAL = 5  # (timestamp)                                                  requests information about the visual state of the game be sent if it has changed since the specified UNIX time
MSGTYPE_REQUEST_VOXEL  = 6  # (x,y,z)                                                      requests information about a single voxel be sent
MSGTYPE_REQUEST_ENTITY = 7  # (entity_id)                                                  requests information about a single entity be sent
MSGTYPE_VISUAL_RANGE   = 8  # (x,y,z)                                                      tells the peer what the current visual range is around the avatar
MSGTYPE_VOXEL_UPDATE   = 9  # ((x,y,z),basic_type,specific_type,active_state,intact_state) sends information about a voxel
MSGTYPE_ENTITY_UPDATE  = 10 # (entity_id,x,y,z,basic_type,specific_type,metadata)          sends information about an entity, ID is a UUID
MSGTYPE_ENTITY_GONE    = 11 # (entity_id)                                                  informs peer the specified entity ID is no longer in the game

# spatial queries and movement
MSGTYPE_REQUEST_POS        = 12 # ()                                        request the avatar location
MSGTYPE_AVATAR_POS         = 13 # (x,y,z)                                   tells the peer what the avatar position is
MSGTYPE_MOVE_VECTOR        = 14 # (x,y,z)                                   tells the peer to attempt to move in the specified vector
MSGTYPE_REQ_DIST_TO        = 15 # (x,y,z)                                   requests the distance to specified coordinates
MSGTYPE_RESP_DIST_TO       = 16 # (x,y,z,dist,msg_id)                       reply for REQ_DIST_TO, msg_id is the msg_id of request
MSGTYPE_REQ_NEAREST_VOXEL  = 17 # (basic_type,extended_type)                requests the nearest voxel of specified type
MSGTYPE_RESP_NEAREST_VOXEL = 18 # (basic_type,extended_type,(x,y,z),msg_id) reply for REQ_NEAREST_VOXEL
MSGTYPE_WALK_TO_POINT      = 19 # (x,y,z)                                   request to walk to the specified location using pathfinding if possible
MSGTYPE_LOOK_AT_POINT      = 20 # (x,y,z)                                   request to look at the specified location
MSGTYPE_WALK_TO_ENTITY     = 21 # (entity_id)                               request to walk to the specified entity once
MSGTYPE_FOLLOW_ENTITY      = 22 # (entity_id)                               request to follow the specified entity
MSGTYPE_FOLLOWING_ENTITY   = 23 # (entity_id,msg_id)                        response to FOLLOW_ENTITY confirming follow
MSGTYPE_UNFOLLOW_ENTITY    = 24 # ()                                        request to stop following entity currently being followed
MSGTYPE_HALT_MOVEMENT      = 25 # ()                                        request to stop moving, also clears current follow target etc
MSGTYPE_REQUEST_VELACC     = 26 # ()                                        request the current velocity and acceleration of the avatar
MSGTYPE_AVATAR_VELACC      = 27 # ((vel_x,vel_y,vel_z),(acc_x,acc_y,acc_z)  tells the peer the current avatar velocity and acceleration

YATE_KEEPALIVE_TIMEOUT = 5 # in seconds

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
    yatelog.debug('yateproto.py','Sent message %s to %s:%s' % (str([msgtype_str[msgtype],params,msgid]),addr[0],addr[1]))
    return msgid


# only in python can you do black magic like this
msgtype_str = {}
for item in dir(sys.modules[__name__]):
    if item.startswith('MSGTYPE_'):
       msgtype_str[getattr(sys.modules[__name__],item)] = item
