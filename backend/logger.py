import logging
from logging_context import request_id_ctx

class RequestIdAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        return f"[req:{request_id_ctx.get()}] {msg}", kwargs

def get_logger(name: str):
    return RequestIdAdapter(logging.getLogger(name), {})
