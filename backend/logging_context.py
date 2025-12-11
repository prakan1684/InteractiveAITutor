import contextvars


request_id_ctx = contextvars.ContextVar("request_id", default="-")