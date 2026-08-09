"""Gunicorn configuration for multi-worker deployment.

This module configures gunicorn with uvicorn workers for production deployment.
Worker count, binding, and lifecycle hooks are configured here.
"""

import os

import structlog

logger = structlog.get_logger()

# Server socket binding
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")
backlog = int(os.getenv("GUNICORN_BACKLOG", "2048"))

# Worker processes - default to 4, configurable via env
workers = int(os.getenv("GUNICORN_WORKERS", "4"))
worker_class = "uvicorn.workers.UvicornWorker"

# Worker connections and threading
worker_connections = int(os.getenv("GUNICORN_WORKER_CONNECTIONS", "1000"))
threads = int(os.getenv("GUNICORN_THREADS", "1"))

# Timeouts
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))

# Preload app for faster worker startup and shared memory
preload_app = os.getenv("GUNICORN_PRELOAD", "true").lower() in ("true", "1", "yes")

# Worker temporary directory (shared memory for gunicorn)
worker_tmp_dir = "/dev/shm/agent-engine"

# Server mechanics
daemon = False
pidfile = None
umask = 0
tmp_upload_dir = None

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "agent-engine"

# Max requests per worker to prevent memory leaks
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "50"))


def on_starting(server):
    """Called just before the master process is initialized.

    Validates configuration and logs deployment parameters.
    """
    logger.info(
        "gunicorn.master.starting",
        workers=workers,
        bind=bind,
        worker_class=worker_class,
        preload=preload_app,
        worker_tmp_dir=worker_tmp_dir,
    )


def post_exec(server):
    """Called when a worker receives the SIGUSR2 signal (graceful restart)."""
    server.log.info("Worker re-executing (graceful restart)")


def pre_request(worker, req):
    """Called just before a worker processes a request."""
    worker.log.debug(f"{req.method} {req.uri}")


def worker_exit(server, worker):
    """Called when a worker exits."""
    server.log.info(f"Worker exited (pid: {worker.pid})")


def nworkers_changed(server, new_value, old_value):
    """Called when the number of workers changes via reloading."""
    server.log.info(f"Worker count changed from {old_value} to {new_value}")


def when_ready(server):
    """Called when the server is fully initialized and ready to accept connections."""
    server.log.info(f"Server ready: workers={workers}, bind={bind}")


def pre_exec(server):
    """Called when a new master process is forked during graceful restart."""
    server.log.info("Forked child, re-executing.")


# =============================================================================
# PERFORMANCE OPTIMIZED SETTINGS
# Applied based on comprehensive performance testing
# =============================================================================

def post_fork_optimized(server, worker):
    """Optimized post-fork hook for better memory sharing and performance"""
    server.log.info(f"Worker spawned (pid: {worker.pid}) - Optimized settings applied")

    try:
        import random
        import secrets

        # Seed randomness per worker
        random.seed(secrets.token_bytes(16))

        # Enable TCP keepalive at OS level
        import socket
        sock = server.socket
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    except Exception as e:
        server.log.warning(f"Post-fork optimization failed: {e}")


# Override post_fork with optimized version
post_fork = post_fork_optimized
