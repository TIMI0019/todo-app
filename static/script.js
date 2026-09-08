const navItems = document.querySelectorAll('.nav-item');
const panels = document.querySelectorAll('.panel');
navItems.forEach(item => {
  item.addEventListener('click', () => {
    navItems.forEach(n => n.classList.remove('active'));
    panels.forEach(p => p.classList.remove('active'));
    item.classList.add('active');
    document.getElementById(item.dataset.target).classList.add('active');
  });
});


// this is where we handle the dark mode toggle functionality. When the user clicks the theme toggle button, we check the current theme and switch it accordingly. We also update the theme state text to reflect the current theme.



const themeToggle = document.getElementById('themeToggle');
const themeState = document.getElementById('themeState');
themeToggle.addEventListener('click', () => {
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  if (isDark) {
    document.documentElement.removeAttribute('data-theme');
    themeState.textContent = '☀️';
  } else {
    document.documentElement.setAttribute('data-theme', 'dark');
    themeState.textContent = '🌙';
  }
});

const taskInput = document.getElementById('taskInput');
const addTaskBtn = document.getElementById('addTaskBtn');
const taskList = document.getElementById('taskList');

function renderTasks(tasks) {
  taskList.innerHTML = '';
  tasks.forEach(task => {
    const li = document.createElement('li');
    li.className = task.done ? 'item done' : 'item';
    li.dataset.id = task.id;
    li.innerHTML = `<input type="checkbox" class="done-check" ${task.done ? 'checked' : ''} title="Mark done"><span>${task.description}</span><input type="checkbox" class="select-check" title="Select to delete"><span class="delete">Remove</span>`;
    taskList.appendChild(li);
  });
}

function addTask() {
  const text = taskInput.value.trim();
  if (!text) return;
  fetch('/api/tasks/add', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ description: text })
  })
    .then(response => response.json())
    .then(tasks => {
      renderTasks(tasks);
      taskInput.value = '';
    });
}
addTaskBtn.addEventListener('click', addTask);
taskInput.addEventListener('keydown', e => { if (e.key === 'Enter') addTask(); });

taskList.addEventListener('click', e => {
  const li = e.target.closest('li');
  if (!li) return;
  const id = parseInt(li.dataset.id);

  if (e.target.classList.contains('done-check')) {
    fetch('/api/tasks/toggle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: id })
    })
      .then(response => response.json())
      .then(tasks => renderTasks(tasks));
  }

  if (e.target.classList.contains('delete')) {
    fetch('/api/tasks/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids: [id] })
    })
      .then(response => response.json())
      .then(tasks => renderTasks(tasks));
  }
});

document.getElementById('deleteSelectedTasks').addEventListener('click', () => {
  const ids = [];
  taskList.querySelectorAll('.select-check:checked').forEach(cb => {
    ids.push(parseInt(cb.closest('li').dataset.id));
  });
  if (ids.length === 0) return;
  fetch('/api/tasks/delete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids: ids })
  })
    .then(response => response.json())
    .then(tasks => renderTasks(tasks));
});

const noteTitleInput = document.getElementById('noteTitleInput');
const noteContentInput = document.getElementById('noteContentInput');
const addNoteBtn = document.getElementById('addNoteBtn');
const noteList = document.getElementById('noteList');

function renderNotes(notes) {
  noteList.innerHTML = '';
  notes.forEach(note => {
    const card = document.createElement('div');
    card.className = 'note-card';
    card.dataset.id = note.id;
    card.innerHTML = `<p class="title">${note.title}</p><p class="content">${note.content}</p><div class="note-actions"><input type="checkbox" class="select-check" title="Select to delete"><span class="delete">Remove</span></div>`;
    noteList.appendChild(card);
  });
}

addNoteBtn.addEventListener('click', () => {
  const title = noteTitleInput.value.trim();
  const content = noteContentInput.value.trim();
  if (!title) return;
  fetch('/api/notes/add', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: title, content: content })
  })
    .then(response => response.json())
    .then(notes => {
      renderNotes(notes);
      noteTitleInput.value = '';
      noteContentInput.value = '';
    });
});

noteList.addEventListener('click', e => {
  const card = e.target.closest('.note-card');
  if (!card) return;
  const id = parseInt(card.dataset.id);

  if (e.target.classList.contains('title')) {
    card.classList.toggle('expanded');
    return;
  }

  if (e.target.classList.contains('delete')) {
    fetch('/api/notes/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids: [id] })
    })
      .then(response => response.json())
      .then(notes => renderNotes(notes));
  }
});

document.getElementById('deleteSelectedNotes').addEventListener('click', () => {
  const ids = [];
  noteList.querySelectorAll('.select-check:checked').forEach(cb => {
    ids.push(parseInt(cb.closest('.note-card').dataset.id));
  });
  if (ids.length === 0) return;
  fetch('/api/notes/delete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids: ids })
  })
    .then(response => response.json())
    .then(notes => renderNotes(notes));
});

fetch('/api/tasks')
  .then(response => response.json())
  .then(tasks => renderTasks(tasks));

fetch('/api/notes')
  .then(response => response.json())
  .then(notes => renderNotes(notes));

let calYear = 2026;
let calMonth = 9;
const monthNames = ["January","February","March","April","May","June","July","August","September","October","November","December"];
const calLabel = document.getElementById('calLabel');
const calGrid = document.getElementById('calGrid');

function renderCalendar() {
  calLabel.textContent = `${monthNames[calMonth - 1]} ${calYear}`;
  calGrid.innerHTML = '';
  ["Mo","Tu","We","Th","Fr","Sa","Su"].forEach(d => {
    const label = document.createElement('div');
    label.className = 'day-label';
    label.textContent = d;
    calGrid.appendChild(label);
  });
  const firstDay = new Date(calYear, calMonth - 1, 1).getDay();
  const offset = (firstDay === 0) ? 6 : firstDay - 1;
  const daysInMonth = new Date(calYear, calMonth, 0).getDate();
  for (let i = 0; i < offset; i++) {
    const empty = document.createElement('div');
    empty.className = 'day-cell empty';
    calGrid.appendChild(empty);
  }
  const today = new Date();
  for (let day = 1; day <= daysInMonth; day++) {
    const cell = document.createElement('div');
    cell.className = 'day-cell';
    if (day === today.getDate() && calMonth === today.getMonth() + 1 && calYear === today.getFullYear()) {
      cell.classList.add('today');
    }
    cell.textContent = day;
    calGrid.appendChild(cell);
  }
}

document.getElementById('prevMonth').addEventListener('click', () => {
  calMonth--;
  if (calMonth < 1) { calMonth = 12; calYear--; }
  renderCalendar();
});
document.getElementById('nextMonth').addEventListener('click', () => {
  calMonth++;
  if (calMonth > 12) { calMonth = 1; calYear++; }
  renderCalendar();
});

renderCalendar();
