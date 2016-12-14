""" This file contains any misc utility functions that don't belong anywhere else
"""

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
