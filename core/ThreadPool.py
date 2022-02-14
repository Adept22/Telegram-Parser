from queue import Queue

class ThreadPool:
    def __init__(self, num_threads=0, num_queue=None):
        if num_queue is None or num_queue < num_threads:
            num_queue = num_threads
        self.tasks = Queue(num_queue)
        self.threads = num_threads
        for _ in range(num_threads): Worker(self.tasks)
    
    # This function can be called to terminate all the worker threads of the queue
    def terminate(self):
        self.wait_completion()
        for _ in range(self.threads): self.add_task("terminate")
        return None

    # This function can be called to add new work to the queue
    def add_task(self, func, *args, **kargs):
        self.tasks.put((func, args, kargs))

    # This function can be called to wait till all the workers are done processing the pending works. If this function is called, the main will not process any new lines unless all the workers are done with the pending works.
    def wait_completion(self):
        self.tasks.join()
    
    # This function can be called to check if there are any pending/running works in the queue. If there are any works pending, the call will return Boolean True or else it will return Boolean False    
    def is_alive(self):
        if self.tasks.unfinished_tasks == 0:
            return False
        else:
            return True