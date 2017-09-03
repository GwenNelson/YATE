""" This file loads data output from burger and presents a nice API for using it
"""

import json
import os.path

json_filename = os.path.abspath(os.path.join(os.path.dirname(__file__),'burger-1.11.json'))

fd = open(json_filename,'r')
json_data = json.load(fd)[0]
fd.close()

blockid_blocks = {} # maps numeric block IDs to the block data

for k,v in json_data['blocks']['block'].items():
    blockid_blocks[v['numeric_id']] = v
