import time as _time
import os as _os
import signal as _signal
import threading as _threading
import functools as _functools

def safe_cast(t, s, default=None):
  """Cast s to type t. Return None if a ValueError
  or TypeError occurs.
  """
  try:
    return t(s)
  except (ValueError, TypeError):
    return default

def sleep(n):
  """Long-term precise sleep function."""
  start = _time.time()
  while _time.time() - start < n:
    _time.sleep(n - (_time.time() - start))

def read_lines(filePath):
  """Read stripped lines from a file, ignoring empy lines
  and lines starting with a `#`.
  """
  with open(filePath, 'r') as f:
    lines = f.readlines()
  lines = list(map(lambda l:l.strip(), lines))
  lines = [line for line in lines if line and not line.startswith("#")]
  return lines

def graceful_exit(shutdown_time):
  """
  Return a decorator function. Functions decorated with it
  will continue to execute for `shutdown_time` seconds when
  the program is stopped with SIGTERM.
  After that it will be killed with SIGUSR1 and the program will
  exit with status code 1.
  If the function terminates in the given time frame, the program will
  exit with code 0.
  """
  _signal.signal(_signal.SIGUSR1, lambda s,f: exit(1))
  pid = _os.getpid()
  def killer_thread():
    _time.sleep(shutdown_time)
    _os.kill(pid, _signal.SIGUSR1)
  def start_killer_thread(sigTermFlag):
    sigTermFlag.set()
    thread = _threading.Thread(target=killer_thread)
    thread.daemon = True
    thread.start()

  def decorator(fun):
    @_functools.wraps(fun)
    def finishing_fun(*args, **kwargs):
      original_sigTerm = _signal.getsignal(_signal.SIGTERM)
      sigTermFlag = _threading.Event()
      _signal.signal(_signal.SIGTERM, lambda s,f: start_killer_thread(sigTermFlag))
      res = fun(*args, **kwargs)
      _signal.signal(_signal.SIGTERM, original_sigTerm)
      if sigTermFlag.is_set():
        exit(0)
      return res
    return finishing_fun
  return decorator

def first_index(ls, cond):
  """
  Return the first index `i` of the list `ls` such that
  cond(ls, i) is true.
  """
  for i, e in enumerate(ls):
    if cond(ls, i):
      break
  return i
