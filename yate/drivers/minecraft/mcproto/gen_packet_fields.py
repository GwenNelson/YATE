import packets
from bs4 import BeautifulSoup
import urllib2
data = urllib2.urlopen('http://wiki.vg/Protocol').read()

soup = BeautifulSoup(data)


for section in soup.find_all("table","wikitable"):
    for cell in section.descendants:
        print cell
        print cell.name,cell.string
        if cell.name=='td':
           if cell.string.startswith('0x'):                           packet_id     = int(cell.string,16)
           if cell.string in ["Handshaking","Play","Status","Login"]: protocol_mode = cell.string
        print packet_id,protocol_mode
