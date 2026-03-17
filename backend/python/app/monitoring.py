import time
import uuid
import logging
from functools import wraps
from collections import defaultdict
from threading import Lock
import re

logger = logging.getLogger(__name__)

class MetricsCollector:
    def __init__(self):
        self._lock = Lock()
        self._requests = defaultdict(int)
        self._errors = defaultdict(int)
        self._latencies = defaultdict(list)
        self._start_times = {}
    
    def start_request(self, endpoint: str) -> str:
        trace_id = str(uuid.uuid4())
        self._start_times[trace_id] = time.time()
        with self._lock:
            self._requests[endpoint] += 1
        return trace_id
    
    def end_request(self, endpoint: str, trace_id: str, status: int = 200):
        if trace_id in self._start_times:
            latency = time.time() - self._start_times[trace_id]
            del self._start_times[trace_id]
            with self._lock:
                self._latencies[endpoint].append(latency)
                if status >= 400:
                    self._errors[endpoint] += 1
    
    def record_error(self, endpoint: str):
        with self._lock:
            self._errors[endpoint] += 1
    
    def get_metrics(self) -> dict:
        with self._lock:
            metrics = {}
            for endpoint in self._requests:
                latencies = self._latencies[endpoint]
                avg_latency = sum(latencies) / len(latencies) if latencies else 0
                p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) >= 20 else avg_latency
                
                metrics[endpoint] = {
                    "requests": self._requests[endpoint],
                    "errors": self._errors[endpoint],
                    "error_rate": self._errors[endpoint] / self._requests[endpoint] if self._requests[endpoint] > 0 else 0,
                    "avg_latency_ms": round(avg_latency * 1000, 2),
                    "p95_latency_ms": round(p95_latency * 1000, 2)
                }
            return metrics

metrics_collector = MetricsCollector()

def track_metrics(endpoint: str = None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            ep = endpoint or func.__name__
            trace_id = metrics_collector.start_request(ep)
            status = 200
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = 500
                metrics_collector.record_error(ep)
                raise
            finally:
                metrics_collector.end_request(ep, trace_id, status)
        return wrapper
    return decorator

class StructuredLogger:
    @staticmethod
    def log(level: str, event: str, trace_id: str = None, **kwargs):
        log_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "level": level,
            "event": event,
            "trace_id": trace_id or str(uuid.uuid4())[:8],
            **kwargs
        }
        if level == "ERROR":
            logger.error(log_data)
        elif level == "WARNING":
            logger.warning(log_data)
        else:
            logger.info(log_data)
    
    @staticmethod
    def info(event: str, trace_id: str = None, **kwargs):
        StructuredLogger.log("INFO", event, trace_id, **kwargs)
    
    @staticmethod
    def error(event: str, trace_id: str = None, **kwargs):
        StructuredLogger.log("ERROR", event, trace_id, **kwargs)
    
    @staticmethod
    def warning(event: str, trace_id: str = None, **kwargs):
        StructuredLogger.log("WARNING", event, trace_id, **kwargs)

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failures = 0
        self._last_failure_time = None
        self._state = "CLOSED"
        self._lock = Lock()
    
    @property
    def state(self):
        with self._lock:
            if self._state == "OPEN":
                if time.time() - self._last_failure_time > self.recovery_timeout:
                    self._state = "HALF_OPEN"
                    logger.info("Circuit breaker entering HALF_OPEN state")
            return self._state
    
    def call(self, func, *args, **kwargs):
        with self._lock:
            if self._state == "OPEN":
                raise Exception(f"Circuit breaker OPEN, service unavailable")
        
        try:
            result = func(*args, **kwargs)
            with self._lock:
                self._failures = 0
                self._state = "CLOSED"
            return result
        except Exception as e:
            with self._lock:
                self._failures += 1
                self._last_failure_time = time.time()
                if self._failures >= self.failure_threshold:
                    self._state = "OPEN"
                    logger.error(f"Circuit breaker OPEN after {self._failures} failures")
            raise
    
    def reset(self):
        with self._lock:
            self._failures = 0
            self._state = "CLOSED"

circuit_breakers = {}

def get_circuit_breaker(name: str) -> CircuitBreaker:
    if name not in circuit_breakers:
        circuit_breakers[name] = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
    return circuit_breakers[name]

SENSITIVE_WORDS = [
    "政治敏感", "暴力", "赌博", "毒品", "诈骗", "色情", "谣言",
    "反动", "恐怖", "分裂", "颠覆", "卖淫", "嫖娼", "贪污", "贿赂"
]

def contains_sensitive_words(text: str) -> tuple:
    for word in SENSITIVE_WORDS:
        if word in text:
            return True, word
    return False, None

class RateLimiter:
    def __init__(self, rate: int = 60, per: int = 60):
        self.rate = rate
        self.per = per
        self.requests = defaultdict(list)
        self._lock = Lock()
    
    def is_allowed(self, key: str = "default") -> bool:
        with self._lock:
            now = time.time()
            self.requests[key] = [t for t in self.requests[key] if now - t < self.per]
            if len(self.requests[key]) >= self.rate:
                return False
            self.requests[key].append(now)
            return True
    
    def get_remaining(self, key: str = "default") -> int:
        with self._lock:
            now = time.time()
            self.requests[key] = [t for t in self.requests[key] if now - t < self.per]
            return max(0, self.rate - len(self.requests[key]))

rate_limiter = RateLimiter(rate=60, per=60)
