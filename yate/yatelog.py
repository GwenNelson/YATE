import sys
import logging
import traceback

logger = None

def get_logger():
    global logger
    if logger is None:
       logger = logging.getLogger('YATE')
       logger.setLevel(logging.INFO)
       log_handler = logging.StreamHandler()
       formatter   = logging.Formatter('%(asctime)s %(levelname)8s: %(message)s')
       log_handler.setFormatter(formatter)
       logger.addHandler(log_handler)
    return logger

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


