import logging
import inspect


class GlobalTabbingFilter(logging.Filter):
    """
    A great tool for automatically increasing the tabbing before a log message relative to the size of the call stack.
    """

    @classmethod
    def instance(cls):
        if not hasattr(cls, '_instance'):
            # This is the first time we are using this instance...
            setattr(cls, '_min_stack_length', len(inspect.stack()))
            setattr(cls, '_instance', GlobalTabbingFilter())
        return getattr(cls, '_instance')

    def filter(self, record):
        """ Modifies the record as desired. """

        # The log's tab size
        record.tabs = '  '
        # A multiplier
        record.tabs *= 2
        # Add the size of the stack
        record.tabs *= (len(inspect.stack()) - getattr(self, '_min_stack_length'))

        return True


def configure_logger(logger, logging_level=logging.DEBUG):

    # Set the logger's level
    logger.setLevel(logging_level)
    logger.debug(f'Set logger logging level to {logging_level}.')

    # Add the tabbing filter
    logger.addFilter(GlobalTabbingFilter.instance())
    logger.debug(f'Added GlobalTabbingFilter instance to logger.')  # TODO

    # Use the StreamHandler to manage the output format of the logs
    handler = logging.StreamHandler()

    logging_format = '%(name)-12s | %(levelname)-8s | %(asctime)-30s | %(tabs)s %(message)s'
    formatter = logging.Formatter(logging_format)
    handler.setFormatter(formatter)
    logger.debug(f'Set logging formatter to {formatter}.')

    handler.setLevel(logging_level)
    logger.debug(f'Set logging level of stream handler to {logging_level}.')

    logger.addHandler(handler)
    logger.debug(f'Added modified stream handler to logger.')

    return logger

