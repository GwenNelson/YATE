import eventlet
from yate import yatelog
from yate import drivers
from yate import yateserver
from yate.drivers import base
import logging
import argparse

logger = yatelog.get_logger()

parser = argparse.ArgumentParser(description='Start a YATE proxy server')
parser.add_argument('-d','--driver',type=str,help='The driver to use for this session',choices=drivers.available_drivers.keys(),required=True)
parser.add_argument('-v','--verbose',action='store_true',help='Verbose mode: sets logging to DEBUG level')
parser.add_argument('-s','--server',type=str,help='The game server to tell the driver to connect to',default=None)
parser.add_argument('-u','--username',type=str,help='The username to pass to the driver',default='YATEBot')
parser.add_argument('-p','--password',type=str,help='The password to pass to the driver',default=None)
args = parser.parse_args()

if args.verbose:
   logger.setLevel(logging.DEBUG)

yatelog.info('yate_proxy', 'Trying to load driver: %s' % args.driver)
try:
   drivermod = drivers.available_drivers[args.driver]
except Exception,e:
   yatelog.fatal_exception('yate_proxy','Could not load driver')
params_dict = {'server':args.server,'username':args.username,'password':args.password}
yatelog.info('yate_proxy','Loaded driver, starting server with driver params: %s' % str(params_dict))
try:
   driver = drivermod.driver(**params_dict)
   server = yateserver.YATEServer(drivermod.driver,verbose=args.verbose)
except Exception,e:
   yatelog.fatal_exception('yate_proxy','Could not start server')
yatelog.info('yate_proxy','Server running on port %s' % server.get_port())
while True: eventlet.greenthread.sleep(10)
