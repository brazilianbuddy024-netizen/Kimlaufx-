#!/usr/bin/env python3
"""
Daemon launcher — double-forks to create a truly detached process
that survives the parent shell's exit.
"""
import os
import sys
import time

def daemonize():
    """Classic double-fork to create a fully detached daemon."""
    # First fork
    pid = os.fork()
    if pid > 0:
        # Parent waits briefly for child to set up
        time.sleep(1)
        sys.exit(0)

    # Child: create new session
    os.setsid()

    # Second fork
    pid = os.fork()
    if pid > 0:
        sys.exit(0)

    # Grandchild: redirect stdio
    sys.stdout.flush()
    sys.stderr.flush()
    devnull = open(os.devnull, 'r')
    os.dup2(devnull.fileno(), sys.stdin.fileno())
    log = open('/home/z/my-project/server.log', 'a')
    os.dup2(log.fileno(), sys.stdout.fileno())
    os.dup2(log.fileno(), sys.stderr.fileno())

    # Change working directory
    os.chdir('/')

if __name__ == '__main__':
    daemonize()
    # Now run the actual server
    os.execvp(sys.executable, [sys.executable, '/home/z/my-project/server.py'])
