from collections import namedtuple
import threading
import time

TaskResult = namedtuple('TaskResult', 'status, retval, task_id, args, kwargs, einfo, thread_id')


def after_return_handler(task, status, retval, task_id, args, kwargs, einfo):
    """
        Setup in conftest.py to receive Task.after_return notifications.

        This function actually gets converted to a method on a Task class, so it has to be a
        function and not a method of TaskTracker.
    """
    result = TaskResult(status, retval, task_id, args, kwargs, einfo, threading.get_ident())
    task_tracker.task_returned(task.name, result)


class CeleryTaskFailure(Exception):
    pass


class TaskTracker:
    """
        Is used when doing Celery integration testing to wait for a specific task to be processed
        before continuing with testing.

        Example:
            from myapp.celery.tasks import save_db_record

            def some_test(self, celery_worker):
                task_tracker.reset()
                save_db_record.delay(1)
                task_tracker.wait_for('myapp.celery.tasks.save_db_record')
                assert ents.DbRecord.count == 1
    """
    def __init__(self):
        self.reset()

    def reset(self):
        self.task_results = {}
        self.slept = 0

    def task_returned(self, task_name, result):
        self.task_results[task_name] = result

    def wait_for(self, dotted_task, throw_failure=True, reset_after=True):
        try:
            while dotted_task not in self.task_results:
                assert self.slept <= 100, 'waited too long for task to complete'
                time.sleep(.05)
                self.slept += 1

            result = self.task_results[dotted_task]
            if result.status != 'SUCCESS' and throw_failure:
                raise CeleryTaskFailure(result)
            return result
        finally:
            if reset_after:
                self.reset()


task_tracker = TaskTracker()
