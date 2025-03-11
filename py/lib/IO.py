import select
from queue import Queue, Empty
from threading import Thread

class Readable:
    def __init__(self, file):
        self.f = file
        self.fd = ''
        self.q = Queue()
        t = Thread(target=self.enqueue_output, args=(self.f, self.q), daemon=True)
        t.start()
        self.readMoreData()
    
    @staticmethod
    def enqueue_output(out, queue):
        while True:
            queue.put(out.read(1))
    
    def readMoreData(self):
        try:
            line = self.q.get_nowait()
            self.fd += line
        except Empty:
            pass

    def read(self, size):
        if not self:
            return ''
        data = self.fd[:size]
        self.fd = self.fd[size:]
        return data
    
    def __getitem__(self, idx):
        assert isinstance(idx, int)
        if len(self.fd) < idx:
            self.readMoreData()
            if len(self.fd) < idx:
                return False
        return True
    
    def __bool__(self):
        if not self.fd:
            self.readMoreData()
        return bool(self.fd)
