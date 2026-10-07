/**
 * StudyMate AI - Background Service Worker
 * Manages communication between Content Scripts, Popup UI, Dashboard, Chrome Storage, and Python Backend API.
 */

const DEFAULT_CONFIG = {
  backendUrl: 'http://localhost:5000/api',
  moodleUrl: 'http://moodle.local',
  aiProvider: 'google', // 'google' | 'claude' | 'groq' | 'openai' | 'deepseek' | 'ollama' | 'fallback'
  aiModel: '',
  aiApiKey: '',
  autoSubmit: false,
  autoScan: true,
  debugMode: true
};

// Initialize default settings on installation
chrome.runtime.onInstalled.addListener(async () => {
  console.log('[StudyMate AI] Extension Installed / Updated');
  const stored = await chrome.storage.local.get(['config', 'tasks', 'history']);
  if (!stored.config) {
    await chrome.storage.local.set({ config: DEFAULT_CONFIG });
  } else {
    // Merge new config keys
    await chrome.storage.local.set({ config: { ...DEFAULT_CONFIG, ...stored.config } });
  }
  if (!stored.tasks) {
    await chrome.storage.local.set({ tasks: [] });
  }
  if (!stored.history) {
    await chrome.storage.local.set({ history: [] });
  }
});

/**
 * Helper to fetch config
 */
async function getConfig() {
  const data = await chrome.storage.local.get('config');
  return { ...DEFAULT_CONFIG, ...(data.config || {}) };
}

/**
 * Make API request to StudyMate AI Backend
 */
async function apiRequest(endpoint, options = {}) {
  const config = await getConfig();
  const base = config.backendUrl.replace(/\/$/, '');
  const path = endpoint.replace(/^\//, '');
  const url = `${base}/${path}`;

  const defaultOptions = {
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    }
  };

  const fetchOptions = {
    ...defaultOptions,
    ...options,
    headers: {
      ...defaultOptions.headers,
      ...(options.headers || {})
    }
  };

  try {
    const response = await fetch(url, fetchOptions);
    const data = await response.json();
    return {
      success: response.ok,
      status: response.status,
      ...data,
      data: data
    };
  } catch (error) {
    console.warn(`[StudyMate AI] API error calling ${url}:`, error);
    return {
      success: false,
      status: 0,
      error: error.message || 'Network error / Backend unreachable'
    };
  }
}

/**
 * Message Router
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const action = message.type || message.action;

  handleMessage(action, message, sender).then(response => {
    sendResponse(response);
  }).catch(error => {
    console.error('[StudyMate AI] Message handler error:', error);
    sendResponse({ success: false, error: error.message });
  });

  return true; // Keep channel open for async response
});

async function handleMessage(action, message, sender) {
  switch (action) {
    // 1. Check Backend Health & Active AI Provider
    case 'CHECK_BACKEND_HEALTH': {
      const res = await apiRequest('/health');
      return res;
    }

    // 2. Get AI Providers & Models
    case 'GET_AI_PROVIDERS': {
      const res = await apiRequest('/ai/providers');
      return res;
    }

    // 3. Moodle page detected from content script
    case 'MOODLE_PAGE_DETECTED': {
      console.log('[StudyMate AI] Moodle page detected:', message.payload);
      await chrome.storage.local.set({
        currentPage: {
          ...message.payload,
          tabId: sender.tab?.id,
          timestamp: new Date().toISOString()
        }
      });
      return { success: true };
    }

    // 4. Scan results from content script
    case 'SYNC_SCANNED_TASK': {
      const task = message.payload;
      console.log('[StudyMate AI] Scanned task received:', task);

      // Save locally to storage
      const storage = await chrome.storage.local.get(['tasks']);
      const tasks = storage.tasks || [];
      const taskId = task.id || task.task_id;
      const existingIdx = tasks.findIndex(t => (t.id || t.task_id) === taskId || (t.title === task.title && (t.course || t.courseName) === (task.course || task.courseName)));

      if (existingIdx >= 0) {
        tasks[existingIdx] = { ...tasks[existingIdx], ...task, updatedAt: new Date().toISOString() };
      } else {
        tasks.push({ ...task, createdAt: new Date().toISOString(), status: task.status || 'Pending' });
      }

      await chrome.storage.local.set({ tasks });

      // Forward to backend API if available
      const backendRes = await apiRequest('/tasks/sync', {
        method: 'POST',
        body: JSON.stringify({ task })
      });

      return { success: true, localTasks: tasks, backendSynced: backendRes.success };
    }

    // 5. Get tasks (from backend or fallback to local storage)
    case 'GET_TASKS': {
      const backendRes = await apiRequest('/tasks');
      if (backendRes.success && Array.isArray(backendRes.tasks)) {
        await chrome.storage.local.set({ tasks: backendRes.tasks });
        return { success: true, tasks: backendRes.tasks, source: 'backend' };
      }
      // Fallback to local storage
      const stored = await chrome.storage.local.get(['tasks']);
      return { success: true, tasks: stored.tasks || [], source: 'local' };
    }

    // 6. Generate AI Solution (passes provider, model, apiKey if configured)
    case 'GENERATE_AI_SOLUTION': {
      const config = await getConfig();
      const payload = message.payload || {};
      const taskId = payload.task_id || payload.taskId;
      const prompt = payload.prompt || payload.custom_prompt || '';
      const context = payload.context || '';
      const provider = payload.provider || config.aiProvider || 'google';
      const model = payload.model || config.aiModel || '';
      const apiKey = payload.api_key || config.aiApiKey || '';

      console.log(`[StudyMate AI] Requesting AI solution for task ${taskId} using ${provider}...`);

      const backendRes = await apiRequest('/ai/generate', {
        method: 'POST',
        body: JSON.stringify({
          task_id: taskId,
          prompt: prompt,
          context: context,
          provider: provider,
          model: model,
          api_key: apiKey
        })
      });

      if (backendRes.success) {
        // Update local task state
        const storage = await chrome.storage.local.get(['tasks']);
        const tasks = storage.tasks || [];
        const tIdx = tasks.findIndex(t => (t.id || t.task_id) == taskId);
        if (tIdx >= 0) {
          tasks[tIdx].status = 'Draft Ready';
          tasks[tIdx].solution = backendRes.solution;
          tasks[tIdx].solutionId = backendRes.solution_id;
          await chrome.storage.local.set({ tasks });
        }
      }

      return backendRes;
    }

    // 7. Save Draft Solution
    case 'SAVE_DRAFT_SOLUTION': {
      const payload = message.payload || {};
      const taskId = payload.task_id || payload.taskId;
      const solutionId = payload.solution_id || payload.solutionId;
      const editedAnswer = payload.edited_answer || payload.editedAnswer;
      const status = payload.status || 'DRAFT';

      const backendRes = await apiRequest('/solutions/draft', {
        method: 'POST',
        body: JSON.stringify({
          task_id: taskId,
          solution_id: solutionId,
          edited_answer: editedAnswer,
          status: status
        })
      });

      // Update local storage
      const storage = await chrome.storage.local.get(['tasks']);
      const tasks = storage.tasks || [];
      const tIdx = tasks.findIndex(t => (t.id || t.task_id) == taskId);
      if (tIdx >= 0) {
        tasks[tIdx].status = status === 'APPROVED' ? 'Approved' : 'In Draft';
        if (tasks[tIdx].solution) {
          tasks[tIdx].solution.edited_answer = editedAnswer;
          tasks[tIdx].solution.status = status;
        }
        await chrome.storage.local.set({ tasks });
      }

      return backendRes.success ? backendRes : { success: true, message: 'Draft saved locally' };
    }

    // 8. Submit Solution
    case 'SUBMIT_SOLUTION': {
      const payload = message.payload || {};
      const taskId = payload.task_id || payload.taskId;
      const solutionId = payload.solution_id || payload.solutionId;
      let targetTabId = payload.tabId;

      console.log(`[StudyMate AI] Submitting solution for task ${taskId}...`);

      // 1. Notify backend
      const backendRes = await apiRequest('/submissions/submit', {
        method: 'POST',
        body: JSON.stringify({
          task_id: taskId,
          solution_id: solutionId
        })
      });

      // 2. Find active Moodle tab if tabId wasn't passed directly
      if (!targetTabId) {
        const tabs = await chrome.tabs.query({});
        const moodleTab = tabs.find(t => t.url && (t.url.includes('mod/assign') || t.url.includes('mod/quiz') || t.url.includes('moodle')));
        if (moodleTab) {
          targetTabId = moodleTab.id;
        }
      }

      // 3. Inject solution into Moodle tab
      if (targetTabId) {
        try {
          const contentRes = await chrome.tabs.sendMessage(targetTabId, {
            type: 'FILL_MOODLE_SUBMISSION',
            payload: payload
          });
          console.log('[StudyMate AI] Injected submission into Moodle:', contentRes);
        } catch (e) {
          console.warn('[StudyMate AI] Could not message content script on tab:', e);
        }
      }

      // Update task status locally & record in history
      const storage = await chrome.storage.local.get(['tasks', 'history']);
      const tasks = storage.tasks || [];
      const history = storage.history || [];
      const tIdx = tasks.findIndex(t => (t.id || t.task_id) == taskId);

      if (tIdx >= 0) {
        tasks[tIdx].status = 'Submitted';
        history.push({
          title: tasks[tIdx].title,
          type: tasks[tIdx].type,
          status: 'Submitted',
          timestamp: new Date().toISOString()
        });
        await chrome.storage.local.set({ tasks, history });
      }

      return backendRes.success ? backendRes : { success: true, message: 'Submission logged' };
    }

    // 9. Trigger active tab page scan
    case 'TRIGGER_ACTIVE_TAB_SCAN': {
      const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!activeTab || !activeTab.id) {
        return { success: false, error: 'No active tab found' };
      }

      try {
        const scanRes = await chrome.tabs.sendMessage(activeTab.id, { type: 'SCAN_PAGE_NOW' });
        return { success: true, scanRes };
      } catch (err) {
        return { success: false, error: 'Could not connect to Moodle page. Make sure you are on a Moodle site.' };
      }
    }

    // 10. Open Full Dashboard
    case 'OPEN_DASHBOARD': {
      const url = chrome.runtime.getURL('dashboard/dashboard.html');
      chrome.tabs.create({ url });
      return { success: true };
    }

    // 11. Update Configuration
    case 'UPDATE_CONFIG': {
      const current = await getConfig();
      const updated = { ...current, ...message.payload };
      await chrome.storage.local.set({ config: updated });
      return { success: true, config: updated };
    }

    default:
      return { success: false, error: `Unknown action: ${action}` };
  }
}
