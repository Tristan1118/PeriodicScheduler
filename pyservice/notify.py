import notify2
from datetime import datetime

PRIO_NONE, PRIO_LOW, PRIO_MID, PRIO_HIGH = range(4)

class Notifier(object):
  """
  Write status updates and errors to a file and send notifications.
  Notifications are given as text and priority.

  The following notifications are sent for each priority:
    PRIO_NONE: No messages are send.
    PRIO_LOW: Message is written to given file.
    PRIO_MID: Message is written to given file and a short
      notification is sent.
    PRIO_HIGH; Message is written to given file and a long
      notification is sent.
  """
  def __init__(self, notifyFile, errorFile, name="", ):
    """
    Args:

      `notifyFile`    File to write messages to.
      `errorFile`     File to write error messages to.
                      This is intended for caught/expected errors,
                      e.g. failed requests to a server, not
                      for exceptions that crash the program.
      `name`          The name of the application.
    """
    self.notifyFile = notifyFile
    self.errorFile = errorFile
    self.name = name
    self._text = f'{name + ": " if name else ""}Check notification file'
    notify2.init(self.name)
    self.notification = notify2.Notification(self._text)
    self._show_notification = False
    self._empty = True

  def add_notification(self, msg, priority):
    """Add a message with the given priority to the notifier.
    See documentation of Notifier for the available priorities.
    """
    self._empty = False
    if priority > PRIO_NONE:
      self._write_to_notify_file(msg, priority)
    if priority >= PRIO_MID:
      self._show_notification = True
    if priority >= PRIO_HIGH:
      self.notification.set_urgency(notify2.URGENCY_CRITICAL)

  def add_error(self, msg):
    """Write msg to the error file."""
    current_time = datetime.now().strftime("%d.%m, %H:%M")
    msg = f'{current_time} Caught error >> {msg}\n'
    with open(self.errorFile, 'a') as f:
      f.write(msg)

  def show_notifications(self):
    """Show any queued up notifications and write
    a delimiter to the notifyFile. Call periodically
    to flush notifications.
    """
    if not self._empty:
      with open(self.notifyFile, 'a') as f:
        f.write('-'*40 + '\n')
    if self._show_notification:
      self.notification.show()
    self._reset()

  def _reset(self):
    """Reset private attributes."""
    self._show_notification = False
    self.notification.set_urgency(notify2.URGENCY_NORMAL)
    self._empty = True


  def _write_to_notify_file(self, msg, priority):
    """Write to the notifyFile, adding the current time."""
    current_time = datetime.now().strftime("%d.%m, %H:%M")
    msg = f'{current_time} ({priority}) >> {msg}\n'
    with open(self.notifyFile, 'a') as f:
      f.write(msg)
