import sys
import logging
import traceback
import curses

logger      = None
formatter   = None

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
    if logger is None:
       logger = logging.getLogger('YATE')
       logger.setLevel(logging.INFO)
       log_handler = CursesHandler(curses_win)
       log_handler.setFormatter(get_formatter())
       logger.curses_win = curses_win
       logger.addHandler(log_handler)
    return logger

def get_logger():
    global logger
    if logger is None:
       logger = logging.getLogger('YATE')
       logger.setLevel(logging.INFO)
       log_handler = logging.StreamHandler()
       log_handler.setFormatter(get_formatter())
       logger.addHandler(log_handler)
    return logger

def info(component,message):
    """ Log general info stuff
    """
    logger.info('%s: %s',component,message)

def minor_exception(component,message):
    """ Log an exception, but keep running
    """
    e_str   = traceback.format_exc()
    logger.error('%s: %s: Exception occurred',component,message)
    for line in e_str.split('\n'):
        logger.error('%s: %s',component,line)

def fatal_exception(component,message):
    e_str   = traceback.format_exc()
    logger.critical('%s: Critical error occurred: %s',component,message)
    for line in e_str.split('\n'):
        if len(line)>1: logger.critical('%s: %s',component,line)

    logger.critical('%s: Terminating',component)
    sys.exit()


