from task import Task
from note import Note
from calender import Calender

import json
import os


SAVE_FILE = "todo_save.json"

def save_data(username, tasks, notes):
    tasks_data = []
    for task in tasks:
        task_dict = {"description": task.description, "done": task.done}
        tasks_data.append(task_dict)

    notes_data = []
    for note in notes:
        note_dict = {
            "title": note.title,
            "content": note.content,
            "date": str(note.date),
            "time": str(note.time)
        }
        notes_data.append(note_dict)

    data = {"username": username, "tasks": tasks_data, "notes": notes_data}

    with open(SAVE_FILE, "w") as f:
        json.dump(data, f)
        
if os.path.exists(SAVE_FILE):
    with open (SAVE_FILE, "r") as f:
        saved_data = json.load(f)
        username = saved_data["username"]
        answer = input(f"welcome back, {username}! Is this you? (yes/no):")
        
        if answer == "yes":
            tasks = []
            notes = []
            for task_dict in saved_data["tasks"]:
                new_task = Task(task_dict["description"])
                new_task.done = task_dict["done"]
                tasks.append(new_task)
            for note_dict in saved_data["notes"]:
                new_note = Note(note_dict["title"], note_dict["content"])
                new_note.date = note_dict["date"]
                new_note.time = note_dict["time"]
                notes.append(new_note)
        else:
            username = input("Enter your username:")
            tasks = []   
            notes = []     
else:
    username = input("Enter your username:")         
    tasks = []
    notes = []
cal = Calender()
while True:
    
    print("1. Add a task")
    print("2. View tasks")
    print("3. Mark task as done")
    print("4. Delete task")
    print("5. Add a note")
    print("6. View notes")
    print("7. Delete note")
    print("8. View calendar")
    print("9. Next month")
    print("10. Previous month")
    print("11. Quit")

    choice = input("Choose an option: ")

    if choice == "1":
        description = input("Enter task description: ")
        new_task = Task(description)
        tasks.append(new_task)

    elif choice == "2":
        if not tasks:
            print("No tasks found. Please add a task first.")
        else:
            for index, task in enumerate(tasks):
                mark = "[x]" if task.done else "[ ]"
                print(f"{index + 1}. {mark} {task.description}")

    elif choice == "3":
        if not tasks:
            print("No tasks found. please add a task first")
        else:
            for index, task in enumerate(tasks): 
                print(f"{index + 1}. {task.description}") 

            raw = input("Which task number(s)? (comma-separated, e.g. 1,3,5): ") 
            if "-" in raw:
                print("Please use commas to separate task numbers, not dashes.")
                continue

            try:
                task_numbers = [int(x.strip()) for x in raw.split(",")]
            except ValueError:
                print("Please enter numbers only, separated by commas (e.g. 1,3,5).")
                continue

            task_indices = [num - 1 for num in task_numbers]

            for task_index in task_indices:
                if task_index < 0 or task_index >= len(tasks):
                    print(f"Task {task_index + 1} doesn't exist — skipped.")
                else:
                    tasks[task_index].done = True
                    print(f"Task {task_index + 1} marked as done")

    elif choice == "4":
        if not tasks:
            print("No task found. Please add a task first.")
        else:
            for index, task in enumerate(tasks):
                print(f"{index + 1}. {task.description}")

            raw = input("Which task number(s) to delete? (comma-separated, e.g. 1,3,5): ")
            if "-" in raw:
                print("Please use commas to separate task numbers, not dashes.")
                continue

            try:
                task_numbers = [int(x.strip()) for x in raw.split(",")]
            except ValueError:
                print("Please enter numbers only, separated by commas (e.g. 1,3,5).")
                continue

            task_indices = [num - 1 for num in task_numbers]
            task_indices.sort(reverse=True)  # delete from the end first, avoids index shifting

            for task_index in task_indices:
                if task_index < 0 or task_index >= len(tasks):
                    print(f"Task {task_index + 1} doesn't exist — skipped.")
                else:
                    deleted_task = tasks.pop(task_index)
                    print(f"Deleted: {deleted_task.description}")
    elif choice == "5":
        title = input("Enter note title: ")
        content = input("Enter note content: ")
        note = Note(title, content)
        notes.append(note)

    elif choice == "6":
        if not notes:
            print("No notes found. Please add a note first.")
        else:
            for note in notes:
                note.display()

    elif choice == "7":
        if not notes:
            print("No notes found. Please add a note first.")
        else:
            for index, note in enumerate(notes):
                print(f"{index + 1}. {note.title}")

            raw = input("Which note number(s) to delete? (comma-separated, e.g. 1,3,5): ")
            if "-" in raw:
                print("Please use commas to separate note numbers, not dashes.")
                continue

            try:
                note_numbers = [int(x.strip()) for x in raw.split(",")]  
            except ValueError:
                print("Please enter numbers only, separated by commas (e.g. 1,3,5).")
                continue

            note_indices = [num - 1 for num in note_numbers]        
            note_indices.sort(reverse=True)

            for note_index in note_indices:
                if note_index < 0 or note_index >= len(notes):
                    print(f"Note {note_index + 1} doesn't exist — skipped.")
                else:
                    deleted_note = notes.pop(note_index)                            
                    print(f"Deleted: {deleted_note.title}")
                    
    elif choice == "8":
        cal.display()
    elif choice == "9":
        cal.next_month()
        cal.display()
    elif choice == "10":
        cal.previous_month()
        cal.display()                    

    elif choice == "11":
        save_data(username, tasks, notes)
        break
    
    else:
        print("Invalid option, please choose 1-11.")