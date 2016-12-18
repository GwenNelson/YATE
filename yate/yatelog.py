import sys
import logging
import traceback
import curses

logger      = logging.getLogger('YATE')
formatter   = None
loglevel    = logging.DEBUG

class CursesHandler(logging.StreamHandler):
   def __init__(self,curses_win=None):
       super(CursesHandler, self).__init__()
       self.curses_win = curses_win
   def emit(self,record):
       global formatter
       s  = ' '
       s += formatter.format(record)
       s += '\n'
       self.curses_win.addstr(s)

def get_formatter():
    global formatter
    if formatter is None:
       formatter = logging.Formatter('%(asctime)s %(levelname)8s: %(message)s')
    return formatter

def get_curses_logger(curses_win):
    global logger
    if not logger.handlers:
       logger = logging.getLogger('YATE')
       logger.setLevel(loglevel)
       log_handler = CursesHandler(curses_win)
       log_handler.setFormatter(get_formatter())
       logger.curses_win = curses_win
       logger.addHandler(log_handler)
    return logger

def get_logger():
    global logger
    if not logger.handlers:
       logger = logging.getLogger('YATE')
       logger.setLevel(loglevel)
       log_handler = logging.StreamHandler()
       log_handler.setFormatter(get_formatter())
       logger.addHandler(log_handler)
    return logger

def info(component,message):
    """ Log general info stuff
    """
    cmp_s = '%10s' % component
    get_logger().info('%s: %s',cmp_s,message)

def debug(component,message):
    if loglevel < logging.DEBUG: return
    cmp_s = '%10s' % component
    get_logger().debug('%s: %s',cmp_s,message)

def warn(component,message):
    cmp_s = '%10s' % component
    get_logger().warn('%s: %s',cmp_s,message)

def minor_exception(component,message):
    """ Log an exception, but keep running
    """
    e_str   = traceback.format_exc()
    get_logger().error('%s: %s: Exception occurred',component,message)
    for line in e_str.split('\n'):
        get_logger().error('%s: %s',component,line)

def fatal_exception(component,message):
    e_str   = traceback.format_exc()
    get_logger().critical('%s: Critical error occurred: %s',component,message)
    for line in e_str.split('\n'):
        if len(line)>1: logger.critical('%s: %s',component,line)

    get_logger().critical('%s: Terminating',component)
    sys.exit()


