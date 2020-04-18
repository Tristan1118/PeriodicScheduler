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

  def __init__(self, timefunc=_time.monotonic, delayfunc=_time.sleep, minDelay=0):
    """
    Sets the `minDelay` attribute which specifies the minimal
    time distance that two actions should have.
    Calls the parent class constructor with the remaining arguments.
    """
    self.minDelay = minDelay
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

    # Adjust the delay by taking the lastExecution into account.
    # If the action should have already been executed
    # (e.g. during a pause of the program), ensure
    # that the delay is not lower than 0.
    if lastExecution is not None:
      delay = delay + lastExecution - self.timefunc()
      delay = 0 if delay < 0 else delay

    # The action has to be scheduled at the
    # first point in time, such that `delay` time units have
    # passed and also the minimal time distance between
    # actions is kept.

    # Get the delays (from now) of the upcoming events in the queue.
    # Insert a 0 in the beginning to guarantee that actions are
    # executed with the minimal time distance.
    # Additionally, insert a ficitonal action at the end of the
    # queue to guarantee that the action can be scheduled between
    # two events. This is purely for algorithmic ease/eliminating
    # edge cases.
    delayList = [0]
    delayList += [e.time - self.timefunc() for e in self.queue]
    delayList.append(delayList[-1] + 2*delay + 2*self.minDelay)

    # Find the first slot between two actions such that the
    # above mentioned requirements are met.
    slot = util.first_index(
      delayList,
      lambda l, i: (l[i+1] >= self.minDelay + delay and
                    l[i+1] >= 2*self.minDelay + l[i])
    )
    # The action can now be scheduled between action `slot`
    # and `slot`+1. Ensure that the action is scheduled
    # at least `delay` time units from now and `minDelay`
    # time units from the previous action.
    delay = max(delayList[slot] + self.minDelay, delay)
    self._enter(delay, priority, periodicAction)

  def _push_event(self, ind, delay):
    """
    Pushes the event in the `ind` position of the queue back
    by `delay` time units.

    Recursively call `_push_event` to
    push back all subsequent events in order to keep
    the minimal time distance between actions.
    """

    # The last event in the queue only needs to be pushed back
    # since there are no subsequent events. This is the base
    # case of the recursion.
    if ind == len(self.queue) - 1:
      self._delay_event(self.queue[ind], delay)
      return True

    # The next event needs to be pushed back sufficiently much such
    # that minDelay is kept between the events.
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
      action(*args, **kwargs)
      new_action = self.periodic(delay, priority, action, args, kwargs)
      self.enter(delay, priority, new_action)
    return periodic_action

"""
set up watchtdog with ~ 2 min timer.
sleep functiton wakes up every minute and sets an event.
as soon as the event is set (while not event.set()), the
watchdog resets it and waits 2 min.
If it wakes up after two min, set an event to True (reschedule event).
The periodic decorator makes every job check for this event. (note
that this job will already be popped off queue). If it is set,
reschedule the remaining events, using pushback.
That way, when the computer wakes up after a long time
without the process being killed (waiting state) and thus
still having scheduled events, exactly one event will be
executed immediately while the remaining ones will be
rescheduled with MINDELAY. Note that the first event
will always have to be pushed back MINDELAY (not 0),
because the only way that the reschedule event will be
called is by executing a job.
"""
