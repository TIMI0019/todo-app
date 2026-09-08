import calendar
import datetime

class Calender:
    def __init__(self):
        today = datetime.date.today()
        self.year = today.year
        self.month = today.month
    def display(self):
        cal = calendar.month(self.year, self.month)
        print(cal)
    def next_month(self):
        self.month += 1
        if self.month > 12:
            self.month = 1
            self.year += 1
    def previous_month(self):
        self.month -= 1
        if self.month < 1:
            self.month = 12
            self.year -= 1            
        
if __name__ == "__main__":
    cal = Calender()
    cal.display()
    
    print ("Going to next month...")
    cal.next_month()
    cal.display()
    
    print ("Going to previous month ...")
    cal.previous_month()
    cal.display()