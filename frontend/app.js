// ============================================================================
// TaskBoard SPA - Complete Client-Side Application
// ============================================================================

(function() {
  'use strict';

  // ==========================================================================
  // SECTION 1: State & Configuration
  // ==========================================================================

  // Status mapping between backend (hyphen) and frontend (underscore)
  const STATUS_MAP = { 
    'todo': 'todo', 
    'in-progress': 'in_progress', 
    'review': 'review', 
    'done': 'done' 
  };
  
  const STATUS_REVERSE = { 
    'todo': 'todo', 
    'in_progress': 'in-progress', 
    'review': 'review', 
    'done': 'done' 
  };

  // Global application state
  const state = {
    token: localStorage.getItem('token'),
    currentUser: null,
    currentProjectId: null,
    projects: [],
    tasks: [],
    users: [],
    ws: null,
    wsReconnectAttempts: 0,
    wsMaxReconnectAttempts: 10,
    wsReconnectDelay: 1000,
    wsPingInterval: null,
    openTaskId: null,  // currently open task in modal
  };

  const API_BASE = '';  // Same origin, no prefix needed for /api routes

  // ==========================================================================
  // SECTION 2: Utility / Toast Notifications
  // ==========================================================================

  function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span>${message}</span><button class="toast-close" onclick="this.parentElement.remove()">&times;</button>`;
    container.appendChild(toast);
    setTimeout(() => {
      toast.classList.add('removing');
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  function formatDate(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  function formatDateTime(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // ==========================================================================
  // SECTION 3: API Client
  // ==========================================================================

  async function apiRequest(url, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    if (state.token) {
      headers['Authorization'] = `Bearer ${state.token}`;
    }
    try {
      const response = await fetch(`${API_BASE}${url}`, { ...options, headers });
      if (response.status === 401) {
        logout();
        throw new Error('Session expired');
      }
      if (response.status === 204) return null;
      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(err.detail || 'Request failed');
      }
      return await response.json();
    } catch (error) {
      if (error.message !== 'Session expired') {
        showToast(error.message, 'error');
      }
      throw error;
    }
  }

  // Auth API
  const api = {
    login: (username, password) => apiRequest('/api/auth/login', {
      method: 'POST', body: JSON.stringify({ username, password })
    }),
    register: (username, email, password) => apiRequest('/api/auth/register', {
      method: 'POST', body: JSON.stringify({ username, email, password })
    }),
    getMe: () => apiRequest('/api/auth/me'),

    // Users
    getUsers: () => apiRequest('/api/users/'),
    
    // Projects
    getProjects: () => apiRequest('/api/projects/'),
    createProject: (data) => apiRequest('/api/projects/', { method: 'POST', body: JSON.stringify(data) }),
    updateProject: (id, data) => apiRequest(`/api/projects/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    deleteProject: (id) => apiRequest(`/api/projects/${id}`, { method: 'DELETE' }),
    
    // Tasks
    getTasks: (projectId) => apiRequest(`/api/projects/${projectId}/tasks`),
    createTask: (projectId, data) => apiRequest(`/api/projects/${projectId}/tasks`, { method: 'POST', body: JSON.stringify(data) }),
    getTask: (taskId) => apiRequest(`/api/tasks/${taskId}`),
    updateTask: (taskId, data) => apiRequest(`/api/tasks/${taskId}`, { method: 'PUT', body: JSON.stringify(data) }),
    deleteTask: (taskId) => apiRequest(`/api/tasks/${taskId}`, { method: 'DELETE' }),
    
    // Subtasks
    getSubtasks: (taskId) => apiRequest(`/api/tasks/${taskId}/subtasks`),
    createSubtask: (taskId, data) => apiRequest(`/api/tasks/${taskId}/subtasks`, { method: 'POST', body: JSON.stringify(data) }),
    updateSubtask: (subtaskId, data) => apiRequest(`/api/subtasks/${subtaskId}`, { method: 'PUT', body: JSON.stringify(data) }),
    deleteSubtask: (subtaskId) => apiRequest(`/api/subtasks/${subtaskId}`, { method: 'DELETE' }),
    
    // Comments
    getComments: (taskId) => apiRequest(`/api/tasks/${taskId}/comments`),
    createComment: (taskId, data) => apiRequest(`/api/tasks/${taskId}/comments`, { method: 'POST', body: JSON.stringify(data) }),
    updateComment: (commentId, data) => apiRequest(`/api/comments/${commentId}`, { method: 'PUT', body: JSON.stringify(data) }),
    deleteComment: (commentId) => apiRequest(`/api/comments/${commentId}`, { method: 'DELETE' }),
  };

  // ==========================================================================
  // SECTION 4: Auth Module
  // ==========================================================================

  function showAuth() {
    document.getElementById('auth-section').classList.remove('hidden');
    document.getElementById('app-section').classList.add('hidden');
  }

  function showApp() {
    document.getElementById('auth-section').classList.add('hidden');
    document.getElementById('app-section').classList.remove('hidden');
  }

  function logout() {
    state.token = null;
    state.currentUser = null;
    state.currentProjectId = null;
    localStorage.removeItem('token');
    disconnectWebSocket();
    showAuth();
  }

  async function handleLogin(e) {
    e.preventDefault();
    const username = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;
    try {
      const data = await api.login(username, password);
      state.token = data.access_token;
      localStorage.setItem('token', state.token);
      await initApp();
    } catch (err) {
      // Error already shown by apiRequest
    }
  }

  async function handleRegister(e) {
    e.preventDefault();
    const username = document.getElementById('register-username').value.trim();
    const email = document.getElementById('register-email').value.trim();
    const password = document.getElementById('register-password').value;
    const confirm = document.getElementById('register-confirm-password').value;
    if (password !== confirm) {
      showToast('Passwords do not match', 'error');
      return;
    }
    try {
      await api.register(username, email, password);
      showToast('Account created! Please log in.', 'success');
      toggleAuthForm('login');
    } catch (err) {
      // Error already shown by apiRequest
    }
  }

  function toggleAuthForm(form) {
    document.getElementById('login-form').classList.toggle('hidden', form !== 'login');
    document.getElementById('register-form').classList.toggle('hidden', form !== 'register');
  }

  // ==========================================================================
  // SECTION 5: App Initialization
  // ==========================================================================

  async function initApp() {
    try {
      state.currentUser = await api.getMe();
      document.getElementById('user-display-name').textContent = state.currentUser.username;
      document.getElementById('user-role').textContent = state.currentUser.role;
      showApp();
      
      // Load users for assignee dropdowns
      state.users = await api.getUsers();
      
      // Load projects
      await loadProjects();
    } catch (err) {
      logout();
    }
  }

  // ==========================================================================
  // SECTION 6: Project Sidebar
  // ==========================================================================

  async function loadProjects() {
    try {
      state.projects = await api.getProjects();
      renderProjectList();
      // Auto-select first project if none selected
      if (!state.currentProjectId && state.projects.length > 0) {
        selectProject(state.projects[0].id);
      } else if (state.currentProjectId) {
        selectProject(state.currentProjectId);
      }
    } catch (err) {
      // Error shown by apiRequest
    }
  }

  function renderProjectList() {
    const list = document.getElementById('project-list');
    list.innerHTML = '';
    state.projects.forEach(project => {
      const li = document.createElement('li');
      li.className = `project-item${project.id === state.currentProjectId ? ' active' : ''}`;
      li.dataset.projectId = project.id;
      li.textContent = project.name;
      li.addEventListener('click', () => selectProject(project.id));
      list.appendChild(li);
    });
  }

  async function selectProject(projectId) {
    state.currentProjectId = projectId;
    const project = state.projects.find(p => p.id === projectId);
    if (project) {
      document.getElementById('current-project-name').textContent = project.name;
    }
    renderProjectList(); // Update active highlight
    
    // Close sidebar on mobile
    document.getElementById('sidebar').classList.remove('open');
    document.getElementById('sidebar-overlay').classList.remove('active');
    
    disconnectWebSocket();
    await loadTasks();
    connectWebSocket(projectId);
  }

  async function handleCreateProject() {
    const nameInput = document.getElementById('project-name');
    const descInput = document.getElementById('project-description');
    const name = nameInput.value.trim();
    if (!name) {
      showToast('Project name is required', 'error');
      return;
    }
    try {
      const project = await api.createProject({ name, description: descInput.value.trim() });
      showToast('Project created!', 'success');
      closeModal('project-modal');
      nameInput.value = '';
      descInput.value = '';
      await loadProjects();
      selectProject(project.id);
    } catch (err) {
      // Error shown by apiRequest
    }
  }

  // ==========================================================================
  // SECTION 7: Kanban Board
  // ==========================================================================

  async function loadTasks() {
    if (!state.currentProjectId) return;
    try {
      state.tasks = await api.getTasks(state.currentProjectId);
      renderBoard();
    } catch (err) {
      // Error shown
    }
  }

  function renderBoard() {
    // Clear all columns
    ['todo', 'in_progress', 'review', 'done'].forEach(colId => {
      document.getElementById(`column-${colId}`).innerHTML = '';
    });
    
    // Update counts and render cards per column
    const counts = { todo: 0, in_progress: 0, review: 0, done: 0 };
    
    state.tasks.forEach(task => {
      const htmlStatus = STATUS_MAP[task.status] || task.status;
      counts[htmlStatus] = (counts[htmlStatus] || 0) + 1;
      const column = document.getElementById(`column-${htmlStatus}`);
      if (column) {
        column.appendChild(createTaskCard(task));
      }
    });
    
    // Update count badges
    Object.entries(counts).forEach(([status, count]) => {
      const el = document.getElementById(`count-${status}`);
      if (el) el.textContent = count;
    });
  }

  function createTaskCard(task) {
    const card = document.createElement('div');
    card.className = 'task-card';
    card.draggable = true;
    card.dataset.taskId = task.id;
    
    const assignee = state.users.find(u => u.id === task.assignee_id);
    const assigneeName = assignee ? assignee.username : 'Unassigned';
    
    // Priority badge class
    const priorityClass = `priority-${task.priority}`;
    
    card.innerHTML = `
      <div class="task-title">${escapeHtml(task.title)}</div>
      ${task.description ? `<div class="task-description">${escapeHtml(task.description)}</div>` : ''}
      <div class="task-meta">
        <span class="priority-badge ${priorityClass}">${task.priority}</span>
        <span>${assigneeName}</span>
        ${task.due_date ? `<span>📅 ${formatDate(task.due_date)}</span>` : ''}
      </div>
    `;
    
    // Click to open modal
    card.addEventListener('click', (e) => {
      if (!e.target.closest('.drag-handle')) {
        openTaskModal(task.id);
      }
    });
    
    // Drag events
    card.addEventListener('dragstart', handleDragStart);
    card.addEventListener('dragend', handleDragEnd);
    
    return card;
  }

  // ==========================================================================
  // SECTION 8: Drag and Drop
  // ==========================================================================

  let draggedTaskId = null;

  function handleDragStart(e) {
    draggedTaskId = e.target.dataset.taskId;
    e.target.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', draggedTaskId);
  }

  function handleDragEnd(e) {
    e.target.classList.remove('dragging');
    draggedTaskId = null;
    // Remove all drag-over classes
    document.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));
  }

  function handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    const column = e.currentTarget.closest('.kanban-column');
    if (column) column.classList.add('drag-over');
  }

  function handleDragEnter(e) {
    e.preventDefault();
    const column = e.currentTarget.closest('.kanban-column');
    if (column) column.classList.add('drag-over');
  }

  function handleDragLeave(e) {
    const column = e.currentTarget.closest('.kanban-column');
    // Only remove if we're leaving the column entirely
    if (column && !column.contains(e.relatedTarget)) {
      column.classList.remove('drag-over');
    }
  }

  async function handleDrop(e) {
    e.preventDefault();
    const column = e.currentTarget.closest('.kanban-column');
    if (column) column.classList.remove('drag-over');
    
    const taskId = e.dataTransfer.getData('text/plain');
    if (!taskId) return;
    
    const htmlStatus = column.dataset.status;
    const backendStatus = STATUS_REVERSE[htmlStatus];
    
    try {
      await api.updateTask(parseInt(taskId), { status: backendStatus });
      // Update local state
      const task = state.tasks.find(t => t.id === parseInt(taskId));
      if (task) task.status = backendStatus;
      renderBoard();
      showToast('Task moved!', 'success');
    } catch (err) {
      // Error shown by apiRequest
    }
  }

  function initDragAndDrop() {
    document.querySelectorAll('.column-body').forEach(body => {
      body.addEventListener('dragover', handleDragOver);
      body.addEventListener('dragenter', handleDragEnter);
      body.addEventListener('dragleave', handleDragLeave);
      body.addEventListener('drop', handleDrop);
    });
  }

  // ==========================================================================
  // SECTION 9: Task Detail Modal
  // ==========================================================================

  async function openTaskModal(taskId) {
    state.openTaskId = taskId;
    const modal = document.getElementById('task-modal');
    
    try {
      const task = await api.getTask(taskId);
      
      // Populate form fields
      document.getElementById('task-title').value = task.title;
      document.getElementById('task-description').value = task.description || '';
      document.getElementById('task-status').value = task.status;
      document.getElementById('task-priority').value = task.priority;
      document.getElementById('task-due-date').value = task.due_date ? task.due_date.split('T')[0] : '';
      
      // Populate assignee dropdown
      const assigneeSelect = document.getElementById('task-assignee');
      assigneeSelect.innerHTML = '<option value="">Unassigned</option>';
      state.users.forEach(user => {
        const opt = document.createElement('option');
        opt.value = user.id;
        opt.textContent = user.username;
        if (user.id === task.assignee_id) opt.selected = true;
        assigneeSelect.appendChild(opt);
      });
      
      // Show/hide delete button
      document.getElementById('delete-task-btn').style.display = 'inline-flex';
      
      // Load subtasks and comments
      await Promise.all([
        loadSubtasks(taskId),
        loadComments(taskId),
      ]);
      
      modal.classList.add('active');
    } catch (err) {
      state.openTaskId = null;
    }
  }

  function openNewTaskModal(initialStatus = 'todo') {
    state.openTaskId = null;
    const modal = document.getElementById('task-modal');
    
    // Clear form
    document.getElementById('task-title').value = '';
    document.getElementById('task-description').value = '';
    document.getElementById('task-status').value = initialStatus;
    document.getElementById('task-priority').value = 'medium';
    document.getElementById('task-due-date').value = '';
    
    // Populate assignee dropdown
    const assigneeSelect = document.getElementById('task-assignee');
    assigneeSelect.innerHTML = '<option value="">Unassigned</option>';
    state.users.forEach(user => {
      const opt = document.createElement('option');
      opt.value = user.id;
      opt.textContent = user.username;
      assigneeSelect.appendChild(opt);
    });
    
    // Hide delete button for new tasks
    document.getElementById('delete-task-btn').style.display = 'none';
    
    // Clear subtasks and comments
    document.getElementById('subtasks-container').innerHTML = '';
    document.getElementById('comments-container').innerHTML = '';
    
    modal.classList.add('active');
  }

  async function handleSaveTask() {
    const title = document.getElementById('task-title').value.trim();
    if (!title) {
      showToast('Title is required', 'error');
      return;
    }
    
    const data = {
      title,
      description: document.getElementById('task-description').value.trim(),
      status: document.getElementById('task-status').value,
      priority: document.getElementById('task-priority').value,
      assignee_id: document.getElementById('task-assignee').value ? parseInt(document.getElementById('task-assignee').value) : null,
      due_date: document.getElementById('task-due-date').value || null,
    };
    
    try {
      if (state.openTaskId) {
        // Update existing task
        await api.updateTask(state.openTaskId, data);
        showToast('Task updated!', 'success');
      } else {
        // Create new task
        data.project_id = state.currentProjectId;
        await api.createTask(state.currentProjectId, data);
        showToast('Task created!', 'success');
      }
      closeModal('task-modal');
      await loadTasks();
    } catch (err) {
      // Error shown
    }
  }

  async function handleDeleteTask() {
    if (!state.openTaskId) return;
    if (!confirm('Are you sure you want to delete this task?')) return;
    try {
      await api.deleteTask(state.openTaskId);
      showToast('Task deleted!', 'success');
      closeModal('task-modal');
      await loadTasks();
    } catch (err) {
      // Error shown
    }
  }

  function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
    if (modalId === 'task-modal') {
      state.openTaskId = null;
    }
  }

  // ==========================================================================
  // SECTION 10: Subtasks
  // ==========================================================================

  async function loadSubtasks(taskId) {
    try {
      const subtasks = await api.getSubtasks(taskId);
      renderSubtasks(subtasks);
    } catch (err) {
      // Error shown
    }
  }

  function renderSubtasks(subtasks) {
    const container = document.getElementById('subtasks-container');
    container.innerHTML = '';
    subtasks.forEach(st => {
      const item = document.createElement('div');
      item.className = `subtask-item${st.completed ? ' completed' : ''}`;
      item.innerHTML = `
        <input type="checkbox" ${st.completed ? 'checked' : ''} data-subtask-id="${st.id}">
        <span class="subtask-text">${escapeHtml(st.title)}</span>
        <button class="btn btn-sm btn-danger" data-delete-subtask="${st.id}">&times;</button>
      `;
      
      // Toggle checkbox
      item.querySelector('input[type="checkbox"]').addEventListener('change', async (e) => {
        try {
          await api.updateSubtask(st.id, { completed: e.target.checked });
        } catch (err) { e.target.checked = !e.target.checked; }
      });
      
      // Delete button
      item.querySelector('[data-delete-subtask]').addEventListener('click', async () => {
        try {
          await api.deleteSubtask(st.id);
          item.remove();
        } catch (err) {}
      });
      
      container.appendChild(item);
    });
  }

  async function handleAddSubtask() {
    if (!state.openTaskId) return;
    const title = prompt('Subtask title:');
    if (!title || !title.trim()) return;
    try {
      await api.createSubtask(state.openTaskId, { title: title.trim(), completed: false, task_id: state.openTaskId });
      await loadSubtasks(state.openTaskId);
      showToast('Subtask added!', 'success');
    } catch (err) {}
  }

  // ==========================================================================
  // SECTION 11: Comments
  // ==========================================================================

  async function loadComments(taskId) {
    try {
      const comments = await api.getComments(taskId);
      renderComments(comments);
    } catch (err) {}
  }

  function renderComments(comments) {
    const container = document.getElementById('comments-container');
    container.innerHTML = '';
    comments.forEach(comment => {
      const author = state.users.find(u => u.id === comment.user_id);
      const div = document.createElement('div');
      div.className = 'comment';
      div.innerHTML = `
        <div class="comment-header">
          <span><strong>${escapeHtml(author ? author.username : 'Unknown')}</strong></span>
          <span>${formatDateTime(comment.created_at)}</span>
        </div>
        <div class="comment-body">${escapeHtml(comment.content)}</div>
      `;
      container.appendChild(div);
    });
  }

  async function handleAddComment() {
    if (!state.openTaskId) return;
    const textarea = document.getElementById('comment-text');
    const content = textarea.value.trim();
    if (!content) return;
    try {
      await api.createComment(state.openTaskId, { content, task_id: state.openTaskId });
      textarea.value = '';
      await loadComments(state.openTaskId);
      showToast('Comment added!', 'success');
    } catch (err) {}
  }

  // ==========================================================================
  // SECTION 12: WebSocket Client
  // ==========================================================================

  function connectWebSocket(projectId) {
    if (!state.token || !projectId) return;
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/${projectId}?token=${state.token}`;
    
    try {
      state.ws = new WebSocket(wsUrl);
      
      state.ws.onopen = () => {
        state.wsReconnectAttempts = 0;
        console.log('WebSocket connected');
      };
      
      state.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          handleWebSocketMessage(message);
        } catch (e) {
          console.error('WS message parse error:', e);
        }
      };
      
      state.ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code);
        if (event.code !== 4001 && state.currentProjectId === projectId) {
          scheduleReconnect(projectId);
        }
      };
      
      state.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
      
      // Keepalive ping every 30 seconds
      state.wsPingInterval = setInterval(() => {
        if (state.ws && state.ws.readyState === WebSocket.OPEN) {
          state.ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, 30000);
      
    } catch (err) {
      console.error('WebSocket connection failed:', err);
    }
  }

  function disconnectWebSocket() {
    if (state.wsPingInterval) {
      clearInterval(state.wsPingInterval);
      state.wsPingInterval = null;
    }
    if (state.ws) {
      state.ws.close();
      state.ws = null;
    }
    state.wsReconnectAttempts = 0;
  }

  function scheduleReconnect(projectId) {
    if (state.wsReconnectAttempts >= state.wsMaxReconnectAttempts) {
      showToast('Lost connection to server. Please refresh.', 'warning');
      return;
    }
    const delay = state.wsReconnectDelay * Math.pow(2, state.wsReconnectAttempts);
    state.wsReconnectAttempts++;
    setTimeout(() => {
      if (state.currentProjectId === projectId && state.token) {
        connectWebSocket(projectId);
      }
    }, delay);
  }

  function handleWebSocketMessage(message) {
    const { type, data } = message;
    
    switch (type) {
      case 'task_created': {
        // Add task to local state and re-render
        if (data.project_id === state.currentProjectId) {
          // Fetch the full task to get all fields
          api.getTask(data.id).then(task => {
            const existing = state.tasks.findIndex(t => t.id === task.id);
            if (existing === -1) {
              state.tasks.push(task);
            } else {
              state.tasks[existing] = task;
            }
            renderBoard();
          }).catch(() => {});
        }
        break;
      }
      case 'task_updated': {
        if (data.project_id === state.currentProjectId) {
          api.getTask(data.id).then(task => {
            const idx = state.tasks.findIndex(t => t.id === task.id);
            if (idx !== -1) {
              state.tasks[idx] = task;
            } else {
              state.tasks.push(task);
            }
            renderBoard();
            // If this task is open in modal, refresh it
            if (state.openTaskId === task.id) {
              openTaskModal(task.id);
            }
          }).catch(() => {});
        }
        break;
      }
      case 'task_deleted': {
        state.tasks = state.tasks.filter(t => t.id !== data.id);
        renderBoard();
        // Close modal if viewing deleted task
        if (state.openTaskId === data.id) {
          closeModal('task-modal');
          showToast('This task was deleted by another user', 'info');
        }
        break;
      }
      case 'subtask_created':
      case 'subtask_updated':
      case 'subtask_deleted': {
        // Refresh subtasks if the relevant task modal is open
        if (state.openTaskId === data.task_id) {
          loadSubtasks(data.task_id);
        }
        break;
      }
      case 'comment_added':
      case 'comment_updated':
      case 'comment_deleted': {
        // Refresh comments if the relevant task modal is open
        if (state.openTaskId === data.task_id) {
          loadComments(data.task_id);
        }
        break;
      }
      case 'pong':
        // Keepalive response, ignore
        break;
      default:
        console.log('Unknown WS event:', type, data);
    }
  }

  // ==========================================================================
  // SECTION 13: Event Listeners & Initialization
  // ==========================================================================

  document.addEventListener('DOMContentLoaded', () => {
    // Auth form listeners
    document.getElementById('login-form').addEventListener('submit', handleLogin);
    document.getElementById('register-form').addEventListener('submit', handleRegister);
    
    // Auth form toggle links - find the toggle links inside auth forms
    document.querySelectorAll('[data-auth-toggle]').forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        toggleAuthForm(link.dataset.authToggle);
      });
    });
    // Also handle the auth-link class links (the "Don't have an account? Register" / "Already have an account? Login" links)
    // These links are in the HTML as <a> tags with class "auth-link"
    document.querySelectorAll('.auth-link').forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        // Determine which form to show based on current visibility
        const loginForm = document.getElementById('login-form');
        if (loginForm.classList.contains('hidden')) {
          toggleAuthForm('login');
        } else {
          toggleAuthForm('register');
        }
      });
    });
    
    // Logout
    document.getElementById('logout-btn').addEventListener('click', logout);
    
    // Hamburger menu (mobile sidebar toggle)
    document.querySelector('.hamburger-btn').addEventListener('click', () => {
      document.getElementById('sidebar').classList.toggle('open');
      document.getElementById('sidebar-overlay').classList.toggle('active');
    });
    document.getElementById('sidebar-overlay').addEventListener('click', () => {
      document.getElementById('sidebar').classList.remove('open');
      document.getElementById('sidebar-overlay').classList.remove('active');
    });
    
    // Project modal
    document.getElementById('add-project-btn').addEventListener('click', () => {
      document.getElementById('project-name').value = '';
      document.getElementById('project-description').value = '';
      document.getElementById('project-modal').classList.add('active');
    });
    document.getElementById('save-project-btn').addEventListener('click', handleCreateProject);
    
    // Task modal
    document.getElementById('add-task-btn').addEventListener('click', () => openNewTaskModal('todo'));
    document.getElementById('save-task-btn').addEventListener('click', handleSaveTask);
    document.getElementById('delete-task-btn').addEventListener('click', handleDeleteTask);
    
    // Subtask
    document.getElementById('add-subtask-btn').addEventListener('click', handleAddSubtask);
    
    // Comment
    document.getElementById('add-comment-btn').addEventListener('click', handleAddComment);
    
    // Modal close buttons (×)
    document.querySelectorAll('.modal-close').forEach(btn => {
      btn.addEventListener('click', () => {
        const modal = btn.closest('.modal-overlay');
        if (modal) closeModal(modal.id);
      });
    });
    
    // Close modal on backdrop click
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) closeModal(overlay.id);
      });
    });
    
    // Initialize drag and drop
    initDragAndDrop();
    
    // Check for existing token and auto-login
    if (state.token) {
      initApp();
    } else {
      showAuth();
    }
  });

})();
