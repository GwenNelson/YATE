""" This file contains any misc utility functions that don't belong anywhere else
"""

def round_vector(v):
    """ Rounds a 3D vector into integers
    """
    x = int(round(v[0]))
    y = int(round(v[1]))
    z = int(round(v[2]))
    return (x,y,z)

def calc_range(center,size):
    """ Calculates the co-ordinates that lie within the range defined by the parameters
         center is the location of the center of the range (usually an avatar)
         size is the width,depth and height of the range
        Returns 2 tuples representing the start and end coordinates of the range as 3D coordinates
    """
    center_x,center_y,center_z = center
    width,depth,height         = size
    start_x                    = center_x - (width/2)
    start_y                    = center_y - (depth/2)
    start_z                    = center_z - (height/2)
    end_x                      = start_x + width
    end_y                      = start_y + depth
    end_z                      = start_z + height
    
    return (start_x,start_y,start_z),(end_x,end_y,end_z)

def iter_within(start,end):
    """ Iterates through every point in a 3D space - yields (x,y,z) tuples
    """
    start = round_vector(start)
    end   = round_vector(end)
    for x in xrange(start[0],end[0],1):
        for y in xrange(start[1],end[1],1):
            for z in xrange(start[2],end[2],1):
                yield (x,y,z)

def diff(a,b):
    """ Returns the difference between 2 scalars
    """
    if a>b: return a-b
    if a<b: return b-a
    return 0

def check_within(pos,start,end):
    """ Checks if pos is within the 3D area specified by start and end
        All parameters are tuples specifying coordinates in 3D space
        Each axis in end must be greater than the corresponding axis in start or weird things happen
    """
    start_x,start_y,start_z = start
    end_x,end_y,end_z       = end
    pos_x,pos_y,pos_z       = pos

    if pos_x < start_x: return False
    if pos_x > end_x:   return False
    if pos_y < start_y: return False
    if pos_y > end_y:   return False
    if pos_z < start_z: return False
    if pos_z > start_z: return False
    return True
