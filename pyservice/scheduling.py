import time as _time
import sched as _sched

from . import util


class PeriodicScheduler(_sched.scheduler):
  """
  Schedule periodic jobs, i.e. jobs that should be executed
  periodically with a fixed time delay.
  Aditionally, a minimum time delay can be given so that
  no two actions are executed in a time period smaller than
  the mimimum delay.
  """

  def __init__(self, timefunc=_time.monotonic, delayfunc=_time.sleep, 
               minDelay=0, bufferFactor=1.05):
    """
    Sets the `minDelay` attribute which specifies the minimal
    time distance that two actions should have.
    The minDelay is multiplied with the bufferFactor to
    account for inaccuracies.
    Calls the parent class constructor with the remaining arguments.
    """
    self.minDelay = minDelay
    self._minDelay = minDelay*bufferFactor
    super(PeriodicScheduler, self).__init__(timefunc, delayfunc)

  def _enter(self, *args, **kwargs):
    """Calls the `enter` function of the parent class."""
    super(PeriodicScheduler, self).enter(*args, **kwargs)

  def enter(self, delay, priority, action, args=(), kwargs={}, lastExecution=None):
    """
    Schedule a periodic job with period `delay`.

    If lastExecution is given, it should be a time obtained
    with the time function of the scheduler.
    Every `delay` time units (first: delay units from lastExecution
    or delay units from now), action will be executed
    with the arguments args and kwargs. The priority is passed
    to the enter function of the parent.
    """
    periodicAction = self.periodic(delay, priority, action, args, kwargs)

    if lastExecution is not None:
      delay = delay + lastExecution - self.timefunc()
      delay = 0 if delay < 0 else delay

    # Insert two fictional events (at the beginning and end of the queue)
    # to ensure that there is a feasible slot between two events and to
    # keep the minDelay from now.
    delayList = [0]
    delayList += [e.time - self.timefunc() for e in self.queue]
    delayList.append(delayList[-1] + 2*delay + 2*self._minDelay)

    slot = util.first_index(
      delayList,
      lambda l, i: (l[i+1] >= self._minDelay + delay and
                    l[i+1] >= 2*self._minDelay + l[i])
    )
    # Schedule after event `slot`.
    delay = max(delayList[slot] + self._minDelay, delay)
    self._enter(delay, priority, periodicAction)

  def _push_event(self, ind, delay):
    """
    Pushes the event in the `ind` position of the queue back
    by `delay` time units.

    Recursively call `_push_event` to
    push back all subsequent events in order to keep
    the minimal time distance between actions.
    """

    # Last event has no following events.
    if ind == len(self.queue) - 1:
      self._delay_event(self.queue[ind], delay)
      return True

    next_delay = minDelay - (self.queue[ind+1] - (self.queue[ind] + delay))
    next_delay = 0 if next_delay < 0 else next_delay
    self._push_event(ind+1, next_delay)

    self._delay_event(self.queue[ind], delay)
    return True

  def _delay_event(self, event, delay):
    """
    Delay an already scheduled event by delay time units
    by canceling and rescheduling it. Will throw an error if
    the event is not in the queue.
    """
    time, *args = event
    self.cancel(event)
    self.enterabs(time + delay, *args)

  def periodic(self, delay, priority, action, args=(), kwargs={}):
    """
    Make the execution of a job periodic by making it schedule itself
    after execution.

    Return a function that can be called without
    arguments which first calls action with the arguments args and kwargs
    and then enters the schedule.
    """
    def periodic_action():
      # Double check to ensure that the minDelay is always kept, 
      # even if the program has been waiting (e.g. during computer-standby).
      self._check_min_delay()
      action(*args, **kwargs)
      new_action = self.periodic(delay, priority, action, args, kwargs)
      self.enter(delay, priority, new_action)
    return periodic_action

  def _check_min_delay(self):
    """Check if the next scheduled event is at least
    minDelay time units from now. If not, push it back sufficiently.
    """
    if not self.queue:
      return True
    nextEventTime = self.queue[0].time
    delay = nextEventTime - self.timefunc()
    # Compare with unbuffered minDelay to compensate for the fact
    # that the check is done after the event is popped off the queue.
    if delay < self.minDelay:
      self._push_event(0, self._minDelay-delay)

