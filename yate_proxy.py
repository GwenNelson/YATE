import eventlet
from yate import yatelog
from yate import drivers
from yate import yateserver
from yate.drivers import base
import sys

logger = yatelog.get_logger()

if len(sys.argv)==1:
   print 'Usage: yate_proxy [driver] [gameserver] [username] [password]'
   print '        <driver>      the driver to use for this session'
   print '        [gameserver]  IP endpoint for the gameserver to connect to, passed to the driver - optional'
   print '        [username]    username to pass to the driver - optional'
   print '        [password]    password to pass to the driver - optional'
   print
   print 'Available drivers are: %s' % ', '.join(drivers.available_drivers.keys())
   print
elif len(sys.argv)>=2:
   gameserver = None
   username   = None
   password   = None
   if len(sys.argv)>=3: gameserver = sys.argv[2]
   if len(sys.argv)>=4: username   = sys.argv[3]
   if len(sys.argv)>=5: password   = sys.argv[4]
   yatelog.info('yate_proxy', 'Trying to load driver: %s' % sys.argv[1])
   try:
      drivermod = drivers.available_drivers[sys.argv[1]]
   except Exception,e:
     yatelog.fatal_exception('yate_proxy','Could not load driver')
   yatelog.info('yate_proxy','Loaded driver, starting server')
   try:
      driver = drivermod.driver(server=gameserver,username=username,password=password)
      server = yateserver.YATEServer(drivermod.driver)
   except Exception,e:
      yatelog.fatal_exception('yate_proxy','Could not start server')
   yatelog.info('yate_proxy','Server running on port %s' % server.get_port())
   while True: eventlet.greenthread.sleep(10)
