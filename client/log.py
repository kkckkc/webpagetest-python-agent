import logging


class LevelTruncatingFormatter(logging.Formatter):
    def format(self, record):
        if len(record.name) > 45:
            arr = record.name.split(".")
            record.name = ".".join([p[0] for p in arr[:-1]]) + "." + arr[-1]
        return super(LevelTruncatingFormatter, self).format(record)


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

    ch = logging.StreamHandler()
    ch.setFormatter(LevelTruncatingFormatter('%(asctime)-15s %(levelname)-7s %(name)-45.45s %(message)s'))
    logging.root.addHandler(ch)

    logging.root.setLevel(root)

    for l in loggers:
        logging.getLogger(l).setLevel(level)
