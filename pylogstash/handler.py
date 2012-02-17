import logging
import zmq
import socket
import datetime
import threading

MAX_MESSAGES = 1000


class Handler(logging.Handler):
    """ A logging handler for sending notifications to a 0mq PUSH.
    """
    def __init__(self, connect_strings=['tcp://127.0.0.1:2120'], fields=[], type=None, context=None, queue_length=MAX_MESSAGES):
        logging.Handler.__init__(self)
        self._context = context if context is not None else zmq.Context()
        self.connect_strings = connect_strings
        self.fields = fields
        self.type = type
        self._local = threading.local()
        self._queue_length = queue_length

    @property
    def publisher(self):
        if not hasattr(self._local, 'publisher'):
            # 0mq sockets aren't threadsafe, so bind them into a
            # threadlocal
            self._local.publisher = self._context.socket(zmq.PUB)
            self._local.publisher.setsockopt(zmq.HWM, self._queue_length)

            for connect_string in self.connect_strings:
                self._local.publisher.connect(connect_string)
        return self._local.publisher

    def emit(self, record):
        field_dict = dict([(field, getattr(record, field)) for field in self.fields])
        timestamp = datetime.datetime.utcfromtimestamp(record.created).isoformat()
        field_dict['timestamp'] = timestamp
        host = socket.gethostname()
        message = {
            "@source": record.filename,
            "@tags": ["pylogstash"],
            "@timestamp": timestamp,
            "@type": self.type,
            "@fields": field_dict,
            "@source_host": host,
            "@message": self.format(record)
        }
        self.publisher.send_json(message)
