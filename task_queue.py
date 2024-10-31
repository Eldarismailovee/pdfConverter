import threading
import queue

class TaskQueue:
    def __init__(self, progress_callback=None, max_workers=4):
        self.tasks = queue.Queue()
        self.is_running = False
        self.progress_callback = progress_callback
        self.max_workers = max_workers
        self.lock = threading.Lock()
        self.total_tasks = 0
        self.completed_tasks = 0

    def add_task(self, task, *args, **kwargs):
        self.tasks.put((task, args, kwargs))
        with self.lock:
            self.total_tasks += 1
        if not self.is_running:
            self.start()

    def start(self):
        self.is_running = True
        for _ in range(self.max_workers):
            threading.Thread(target=self.run).start()

    def run(self):
        while not self.tasks.empty():
            try:
                task, args, kwargs = self.tasks.get_nowait()
            except queue.Empty:
                break
            try:
                task(*args, **kwargs)
            except Exception as e:
                print(f"Error: {e}")
            self.tasks.task_done()
            with self.lock:
                self.completed_tasks += 1
                if self.progress_callback:
                    progress = int((self.completed_tasks / self.total_tasks) * 100)
                    self.progress_callback(progress)
        with self.lock:
            if self.tasks.empty():
                self.is_running = False
                self.total_tasks = 0
                self.completed_tasks = 0
