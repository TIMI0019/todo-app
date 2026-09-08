import datetime

class Note:
    def __init__(self, title, content):
        self.title = title
        self.content = content
        now = datetime.datetime.now()
        self.date = now.date()
        self.time = now.time()
        
    def display(self):
        print(f"{self.title} ({self.date})")
        print(self.content)


