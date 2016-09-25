import logging


def init_log(level, *loggers):
    if level is None:
        level = logging.WARN
        root = logging.WARN
    elif level == 1 or level == logging.INFO:
        level = logging.INFO
        root = logging.WARN
    elif level == 2 or level == logging.DEBUG:
        level = logging.DEBUG
        root = logging.WARN
    elif level == 3:
        level = logging.DEBUG
        root = logging.INFO
    else:
        level = logging.DEBUG
        root = logging.DEBUG

    logging.basicConfig(format='%(asctime)-15s %(levelname)-7s %(name)-45.45s %(message)s')
    logging.root.setLevel(root)

    for l in loggers:
        logging.getLogger(l).setLevel(level)
