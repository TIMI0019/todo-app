from task import Task

import json
import os

SAVE_FILE = "todo_save.json"

def save_tasks(username, tasks):
    tasks_data = []
    for task in tasks:
        task_dict = {"description": task.description, "done": task.done}
        tasks_data.append(task_dict)

    data = {"username": username, "tasks": tasks_data}

    with open(SAVE_FILE, "w") as f:
        json.dump(data, f)
        
if os.path.exists(SAVE_FILE):
    with open (SAVE_FILE, "r") as f:
        saved_data = json.load(f)
        username = saved_data["username"]
        answer = input(f"welcome back, {username}! Is this you? (yes/no):")
        
        if answer == "yes":
            tasks = []
            for task_dict in saved_data["tasks"]:
                new_task = Task(task_dict["description"])
                new_task.done = task_dict["done"]
                tasks.append(new_task)
        else:
            username = input("Enter your username:")
            tasks = []        
else:
    username = input("Enter your username:")         
    tasks = []

while True:
    
    print("1. Add a task")
    print("2. View tasks")
    print("3. Mark task as done")
    print("4. Delete task")
    print("5. Quit")

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
            print(f"No tasks found. please add a task first")
        else:
            for index, task in enumerate(tasks): 
                print(f"{index + 1}. {task.description}")              
            task_number = input("Which task number is done?")
            task_number = int(task_number)
            task_index = task_number - 1
            if task_index < 0 or task_index >= len(tasks):
                print ("That task index doesn't exist")
            else:    
                tasks[task_index].done = True
                print("Task marked as done")    
    elif choice == "4":
        if not tasks:
            print("No task found. Please add a task first.")
        else:
            for index, task in enumerate(tasks):
                print(f"{index + 1}. {task.description}")
            task_number = input("Which task do you want to delete?")
            task_number = int(task_number)
            task_index = task_number - 1
            
            if task_index < 0 or task_index >= len(tasks):
                print("That task doesn't exist")
            else:
                deleted_task = tasks.pop(task_index)
                print(f"Deleted: {deleted_task.description}")                  
    elif choice == "5":
        save_tasks(username, tasks)
        break