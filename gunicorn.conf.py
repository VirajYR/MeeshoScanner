# Gunicorn configuration file for production
import multiprocessing

# Server socket
bind = "127.0.0.1:5000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests, to control memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "/home/ubuntu/MeeshoScanner/logs/access.log"
errorlog = "/home/ubuntu/MeeshoScanner/logs/error.log"
loglevel = "info"

# Process naming
proc_name = "meesho_scanner"

# Server mechanics
daemon = False
pidfile = "/home/ubuntu/MeeshoScanner/gunicorn.pid"
user = "ubuntu"
group = "ubuntu"
tmp_upload_dir = None

# SSL (if needed)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"
