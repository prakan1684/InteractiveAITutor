import logging
import sys


LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def setup_logging(level: str="INFO"):
    #prevening duplicate handlers if called multiple time
    root= logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    root.setLevel(level)
    root.addHandler(handler)
    
    # Suppress verbose third-party library logs
    # Azure SDK logs (very verbose HTTP requests/responses)
    logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
    logging.getLogger("azure.core").setLevel(logging.WARNING)
    logging.getLogger("azure.identity").setLevel(logging.WARNING)
    logging.getLogger("azure.storage").setLevel(logging.WARNING)
    
    # ChromaDB telemetry logs
    logging.getLogger("chromadb.telemetry").setLevel(logging.ERROR)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    
    # OpenAI SDK logs
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    # Uvicorn access logs (already handled by uvicorn config, but just in case)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    