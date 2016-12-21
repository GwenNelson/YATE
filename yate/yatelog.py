import os
import sys
import logging
import traceback
import inspect
import curses

logger      = logging.getLogger('YATE')
formatter   = None
loglevel    = logging.INFO

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
    logger = logging.getLogger('YATE')
    if not logger.handlers:
       logger.setLevel(loglevel)
       log_handler = CursesHandler(curses_win)
       log_handler.setFormatter(get_formatter())
       logger.curses_win = curses_win
       logger.addHandler(log_handler)
       logger.all_fatal = False
       logger.no_minor  = False
    return logger

def get_logger():
    logger = logging.getLogger('YATE')
    if not logger.handlers:
       logger.setLevel(loglevel)
       log_handler = logging.StreamHandler()
       log_handler.setFormatter(get_formatter())
       logger.addHandler(log_handler)
       logger.all_fatal = False
       logger.no_minor  = False
    return logger

def info(component,message):
    """ Log general info stuff
    """
    cmp_s = '%10s' % component
    get_logger().info('%s: %s',cmp_s,message)

def debug(component,message):
    cmp_s = '%10s' % component
    get_logger().debug('%s: %s',cmp_s,message)

def error(component,message):
    cmp_s = '%10s' % component
    get_logger().error('%s: %s',cmp_s,message)

def warn(component,message):
    cmp_s = '%10s' % component
    get_logger().warn('%s: %s',cmp_s,message)
    if get_logger().all_fatal:
       get_logger().critical('%s: Always fatal mode is on, terminating',component)
       os._exit(1)

def minor_exception(component,message):
    """ Log an exception, but keep running
    """
    e_type,e_value,e_traceback = sys.exc_info()
    e_str  = ''
    e_str += 'Exception occurred\n'
    e_str += traceback.format_exception_only(e_type,e_value)[0]

    frames = []
    tb = e_traceback
    while tb:
       frames.append(tb.tb_frame)
       tb = tb.tb_next
    frames.reverse()
    for f in frames:
        l_vars = ''
        for k,v in f.f_locals.items():
            v_str = ''
            try:
               v_str = str(v)
            except:
               v_str = '<UNPRINTABLE VALUE>'
            if len(v_str)>=20: v_str = '<MASSIVE STRING>'
            l_vars += '\t%s = %s\n' % (k,v_str)
        source_s = ''
        source_lines,source_line_no = inspect.getsourcelines(f)
        for l in source_lines:
            if (f.f_lineno-source_line_no) <= 2:
               source_s       += '%s >>> %s\n' % (source_line_no,l)
            source_line_no += 1
            if source_line_no > f.f_lineno: break
        e_str += '\n%s, line %s in %s:\n%s\n%s' % (f.f_code.co_filename, f.f_lineno,f.f_code.co_name, source_s ,l_vars)
    for line in e_str.split('\n'):
        if len(line)>2:
           get_logger().error('%s: %s',component,line)
    if get_logger().no_minor:
       get_logger().critical('%s: No minor exceptions, terminating', component)
       os._exit(1)

def fatal_exception(component,message):
    minor_exception(component,message)
    get_logger().critical('%s: Above exception is critical, terminating',component)
    os._exit(1)


