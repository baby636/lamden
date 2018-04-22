import os
from pathlib import Path
import logging, coloredlogs
from logging.config import fileConfig
import sys

# Constants for configuring colored logger
lvl_styles = coloredlogs.DEFAULT_LEVEL_STYLES
COLORS = ('blue', 'cyan', 'green', 'magenta', 'red', 'yellow', 'white')
LVLS = ('debug', 'info', 'warning', 'error', 'critical')
P = pow(2, 31) - 1

# root = logging.getLogger()
# root.propagate = False
# stream_handler = logging.StreamHandler()
# coloredlogs.install(logger=root)
# root.addHandler(stream_handler)


# Class to bridge a stream and a logger. We use this to output stdout/stderr to our log files
class LoggerWriter:
    def __init__(self, level):
        self.level = level

    def write(self, message):
        if message != '\n':
            self.level(message)

    def flush(self):
        return


def get_logger(name='', bg_color=None, auto_bg_val=None):
    def apply_bg_color(lvls, color):
        for lvl in lvls:
            lvl_styles[lvl]['background'] = color
            lvl_styles[lvl]['color'] = 'black'

    if auto_bg_val is not None:
        assert bg_color is None, "Cannot set both bg_color and auto_bg_val (must be one or the other)"
        color = COLORS[(auto_bg_val*P) % len(COLORS)]
        apply_bg_color(LVLS, color)

    if bg_color is not None:
        assert auto_bg_val is None, "Cannot set both bg_color and auto_bg_val (must be one or the other)"
        apply_bg_color(LVLS, bg_color)

    log = logging.getLogger(name)
    coloredlogs.install(level='DEBUG', logger=log, level_styles=lvl_styles, milliseconds=True, reconfigure=False)
    # coloredlogs.install(level='DEBUG', logger=log, level_styles=lvl_styles, milliseconds=True, reconfigure=True)

    # Remove all handlers
    for h in log.handlers:
        log.removeHandler(h)

    return log


path = os.path.dirname(Path(__file__).parents[0])
os.chdir(path)
path += "/conf"
loggerIniFile = path + "/cilantro_logger.ini"
fileConfig(loggerIniFile)
# coloredlogs.install(level='DEBUG')


# root = logging.getLogger()
# stream_handler = logging.StreamHandler(sys.stderr)
# coloredlogs.install(logger=root, handler=stream_handler)
#
# for h in root.handlers:
#     root.removeHandler(h)


# Forward stderr/stdout to loggers (so prints and exceptions can be seen in log files)
out_log = logging.getLogger('STDOUT')
err_log = logging.getLogger("STDERR")
# out_log = get_logger('STDOUT')
# err_log = get_logger('STDERR')
sys.stderr = LoggerWriter(err_log.error)
sys.stdout = LoggerWriter(out_log.debug)


# root.addHandler(stream_handler)



# stream_handler = logging.StreamHandler(sys.stderr)
# coloredlogs.install(handler=stream_handler)
# root = logging.getLogger()
# root.addHandler(stream_handler)