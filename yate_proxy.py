import eventlet
from yate import yatelog
from yate import drivers
from yate import yateserver
import sys

logger = yatelog.get_logger()

if len(sys.argv)==1:
   print 'Usage: yateserver [driver] [gameserver] [username] [password]'
   print '        <driver>      the driver to use for this session'
   print '        [gameserver]  IP endpoint for the gameserver to connect to, passed to the driver - optional'
   print '        [username]    username to pass to the driver - optional'
   print '        [password]    password to pass to the driver - optional'
   print
   print 'Available drivers are: %s' % ', '.join(drivers.available_drivers.keys())
   print
elif len(sys.argv)>=2:
   logger.info('YATEServer: Trying to load driver: %s',sys.argv[1])
   try:
      drivermod = drivers.available_drivers[sys.argv[1]]
   except Exception,e:
     yatelog.fatal_exception('YATEServer','Could not load driver')
   logger.info('YATEServer: Loaded driver, starting server')
   try:
      server = yateserver.YATEServer(drivermod.driver)
   except Exception,e:
      yatelog.fatal_exception('YATEServer','Could not start server')
   logger.info('YATEServer: Server running on port %s', server.get_port())
   while True: eventlet.greenthread.sleep(0)
