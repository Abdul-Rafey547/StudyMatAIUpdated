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
  const stored = await chrome.storage.local.get(['config', 'tasks', 'resources', 'history']);
  if (!stored.config) {
    await chrome.storage.local.set({ config: DEFAULT_CONFIG });
  } else {
    // Merge new config keys
    await chrome.storage.local.set({ config: { ...DEFAULT_CONFIG, ...stored.config } });
  }
  if (!stored.tasks) {
    await chrome.storage.local.set({ tasks: [] });
  }
  if (!stored.resources) {
    await chrome.storage.local.set({ resources: [] });
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

  // If sending POST/PUT/PATCH with application/json header but no body, provide an empty JSON body
  const reqMethod = (fetchOptions.method || 'GET').toUpperCase();
  if (['POST', 'PUT', 'PATCH'].includes(reqMethod) && fetchOptions.body === undefined) {
    fetchOptions.body = JSON.stringify({});
  }

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

      // Save locally to storage with stable deduplication
      const storage = await chrome.storage.local.get(['tasks']);
      const tasks = storage.tasks || [];
      const taskId = task.id || task.task_id || task.moodle_activity_id;
      const existingIdx = tasks.findIndex(t =>
        (t.id || t.task_id) === taskId ||
        (t.moodle_activity_id && task.moodle_activity_id && t.moodle_activity_id === task.moodle_activity_id) ||
        (t.title === task.title && (t.course || t.courseName) === (task.course || task.courseName))
      );

      if (existingIdx >= 0) {
        tasks[existingIdx] = {
          ...tasks[existingIdx],
          ...task,
          updatedAt: new Date().toISOString()
        };
      } else {
        tasks.push({
          ...task,
          createdAt: new Date().toISOString(),
          status: task.status || 'Pending'
        });
      }

      await chrome.storage.local.set({ tasks });

      // Forward to backend API if available
      const backendRes = await apiRequest('/tasks/sync', {
        method: 'POST',
        body: JSON.stringify({ task })
      });

      return { success: true, localTasks: tasks, backendSynced: backendRes.success };
    }

    // 5. Sync Scanned Learning Resources (PDF books, notes, DOCX, Pages, Books)
    case 'SYNC_SCANNED_RESOURCES': {
      const payload = message.payload || {};
      const newResources = payload.resources || (payload.title ? [payload] : []);
      console.log(`[StudyMate AI] Synced ${newResources.length} learning resources.`);

      const storage = await chrome.storage.local.get(['resources']);
      const resources = storage.resources || [];

      newResources.forEach(res => {
        const resId = res.id || res.resource_id || res.moodle_resource_id || res.url;
        const existingIdx = resources.findIndex(r =>
          (r.id && res.id && r.id === res.id) ||
          (r.url && res.url && r.url === res.url) ||
          (r.title === res.title && (r.course || r.courseName) === (res.course || res.courseName))
        );

        if (existingIdx >= 0) {
          resources[existingIdx] = { ...resources[existingIdx], ...res, updatedAt: new Date().toISOString() };
        } else {
          resources.push({ ...res, createdAt: new Date().toISOString() });
        }
      });

      await chrome.storage.local.set({ resources });

      // Sync with backend API
      const backendRes = await apiRequest('/resources/sync', {
        method: 'POST',
        body: JSON.stringify({ resources: newResources })
      });

      return { success: true, localCount: resources.length, backendSynced: backendRes.success };
    }

    // 6. Get tasks (from backend or fallback to local storage)
    case 'GET_TASKS': {
      const pendingOnly = message.pendingOnly ? '?pending_only=true' : '';
      const backendRes = await apiRequest(`/tasks${pendingOnly}`);
      if (backendRes.success && Array.isArray(backendRes.tasks)) {
        await chrome.storage.local.set({ tasks: backendRes.tasks });
        return { success: true, tasks: backendRes.tasks, source: 'backend' };
      }
      // Fallback to local storage
      const stored = await chrome.storage.local.get(['tasks']);
      let localTasks = stored.tasks || [];
      if (message.pendingOnly) {
        localTasks = localTasks.filter(t => t.isActionablePending !== false && t.availabilityStatus !== 'SUBMITTED' && t.availabilityStatus !== 'COMPLETED');
      }
      return { success: true, tasks: localTasks, source: 'local' };
    }

    // 7. Get Learning Resources
    case 'GET_RESOURCES': {
      const courseIdParam = message.courseId ? `?course_id=${message.courseId}` : '';
      const backendRes = await apiRequest(`/resources${courseIdParam}`);
      if (backendRes.success && Array.isArray(backendRes.resources)) {
        await chrome.storage.local.set({ resources: backendRes.resources });
        return {
          success: true,
          resources: backendRes.resources,
          courses: backendRes.courses || [],
          source: 'backend'
        };
      }
      // Fallback to local storage
      const stored = await chrome.storage.local.get(['resources']);
      return { success: true, resources: stored.resources || [], source: 'local' };
    }

    // 8. Generate AI Solution
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

    // 9. Save Draft Solution
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

    // 10. Generate Submission File (DOCX or TXT)
    case 'GENERATE_SUBMISSION_FILE': {
      const payload = message.payload || {};
      const backendRes = await apiRequest('/submissions/generate-file', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      return backendRes;
    }

    // 11. Prepare / Submit Solution to Moodle
    case 'PREPARE_SUBMISSION':
    case 'SUBMIT_SOLUTION': {
      const payload = message.payload || {};
      const taskId = payload.task_id || payload.taskId;
      const solutionId = payload.solution_id || payload.solutionId;
      const fileFormat = payload.format || payload.file_format || 'DOCX';
      let targetTabId = payload.tabId;

      console.log(`[StudyMate AI] Preparing submission for task ${taskId} (Format: ${fileFormat})...`);

      // 1. Generate real assignment file from approved answer
      const fileRes = await apiRequest('/submissions/generate-file', {
        method: 'POST',
        body: JSON.stringify({
          task_id: taskId,
          solution_id: solutionId,
          format: fileFormat,
          answer: payload.answer || payload.edited_answer
        })
      });

      // 2. Find active Moodle tab or create one if needed
      if (!targetTabId) {
        const tabs = await chrome.tabs.query({});
        const moodleTab = tabs.find(t => t.url && (t.url.includes('mod/assign') || t.url.includes('mod/quiz') || t.url.includes('moodle')));
        if (moodleTab) {
          targetTabId = moodleTab.id;
        }
      }

      // If task has specific Moodle URL and no matching tab, open it
      if (!targetTabId && payload.moodle_url) {
        const newTab = await chrome.tabs.create({ url: payload.moodle_url });
        targetTabId = newTab.id;
      }

      // 3. Inject file and text into Moodle tab via content script
      let contentRes = null;
      if (targetTabId) {
        try {
          contentRes = await chrome.tabs.sendMessage(targetTabId, {
            type: 'FILL_MOODLE_SUBMISSION',
            payload: {
              ...payload,
              file_base64: fileRes.file_base64,
              file_name: fileRes.file_name,
              mime_type: fileRes.mime_type,
              data_url: fileRes.data_url
            }
          });
          console.log('[StudyMate AI] Injected submission helper into Moodle:', contentRes);
        } catch (e) {
          console.warn('[StudyMate AI] Could not message content script on tab:', e);
        }
      }

      return {
        success: true,
        fileGenerated: fileRes.success,
        fileName: fileRes.file_name,
        fileDataUrl: fileRes.data_url,
        fileSize: fileRes.file_size,
        injected: Boolean(contentRes && contentRes.success)
      };
    }

    // 12. Truthful Verification Endpoint
    case 'VERIFY_SUBMISSION': {
      const payload = message.payload || {};
      const taskId = payload.task_id || payload.taskId;
      let targetTabId = payload.tabId;

      if (!targetTabId) {
        const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (activeTab) targetTabId = activeTab.id;
      }

      let moodleVerification = null;
      if (targetTabId) {
        try {
          const vRes = await chrome.tabs.sendMessage(targetTabId, { type: 'VERIFY_MOODLE_SUBMISSION' });
          if (vRes && vRes.verification) {
            moodleVerification = vRes.verification;
          }
        } catch (e) {
          console.warn('[StudyMate AI] Could not verify with active tab:', e);
        }
      }

      const moodleStatus = moodleVerification ? moodleVerification.submissionStatus : (payload.moodle_status || '');
      const isVerified = moodleVerification ? moodleVerification.verified : Boolean(payload.verified);

      // Call backend verification
      const backendRes = await apiRequest('/submissions/verify', {
        method: 'POST',
        body: JSON.stringify({
          task_id: taskId,
          solution_id: payload.solution_id,
          moodle_status: moodleStatus,
          verified: isVerified,
          file_name: payload.file_name || moodleVerification?.submissionFiles?.[0] || 'Assignment_Solution.docx',
          file_format: payload.file_format || 'DOCX'
        })
      });

      // Update local storage only if verified
      if (backendRes.verified) {
        const storage = await chrome.storage.local.get(['tasks', 'history']);
        const tasks = storage.tasks || [];
        const history = storage.history || [];
        const tIdx = tasks.findIndex(t => (t.id || t.task_id) == taskId);

        if (tIdx >= 0) {
          tasks[tIdx].status = 'Submitted';
          tasks[tIdx].availabilityStatus = 'SUBMITTED';
          tasks[tIdx].isActionablePending = false;
        }

        history.push({
          taskId: taskId,
          title: tasks[tIdx]?.title || 'Assignment Submission',
          type: 'ASSIGNMENT',
          status: 'Submitted',
          timestamp: new Date().toISOString()
        });

        await chrome.storage.local.set({ tasks, history });
      }

      return backendRes;
    }

    // 13. Study Learning Resource (PDF/Book/Doc)
    case 'STUDY_RESOURCE': {
      const config = await getConfig();
      const payload = message.payload || {};
      const backendRes = await apiRequest('/resources/study', {
        method: 'POST',
        body: JSON.stringify({
          ...payload,
          provider: payload.provider || config.aiProvider,
          model: payload.model || config.aiModel,
          api_key: payload.api_key || config.aiApiKey
        })
      });
      return backendRes;
    }

    // 14. Trigger Reliable Moodle API Scan (Primary source of truth)
    case 'TRIGGER_API_SCAN':
    case 'TRIGGER_ACTIVE_TAB_SCAN': {
      console.log('[StudyMate AI] Triggering Moodle API scan via backend...');
      const backendScan = await apiRequest('/tasks/scan', { method: 'POST', body: JSON.stringify({}) });

      if (backendScan.success) {
        const tasks = backendScan.tasks || [];
        const resources = backendScan.resources || [];
        await chrome.storage.local.set({
          tasks: tasks,
          resources: resources,
          lastScanAt: new Date().toISOString()
        });
        return {
          success: true,
          source: 'api',
          totalTasks: backendScan.total_tasks ?? tasks.length,
          pendingTasks: backendScan.pending_tasks ?? tasks.filter(t => t.is_actionable_pending).length,
          totalResources: backendScan.total_resources ?? resources.length,
          tasks: tasks,
          resources: resources,
          message: backendScan.message || `Found ${tasks.length} tasks and ${resources.length} study materials.`
        };
      }

      // If backend responded with explicit Moodle API or configuration error
      if (backendScan.status > 0) {
        return {
          success: false,
          error: backendScan.error || 'Moodle API scan error. Please check Moodle Web Services configuration.',
          errorcode: backendScan.errorcode
        };
      }

      // Optional DOM fallback only if backend server is completely unreachable
      console.warn('[StudyMate AI] Backend server unreachable. Attempting active tab DOM scan fallback...');
      const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (activeTab && activeTab.id) {
        try {
          const domRes = await chrome.tabs.sendMessage(activeTab.id, { type: 'SCAN_PAGE_NOW' });
          if (domRes && domRes.success) {
            return {
              success: true,
              source: 'dom_fallback',
              domRes,
              message: 'Scanned active tab via DOM fallback (Backend server unreachable).'
            };
          }
        } catch (e) {
          // Ignore content script message error
        }
      }

      return {
        success: false,
        error: backendScan.error || 'StudyMate backend server is not running. Please start app.py.'
      };
    }

    // 15. Open Full Dashboard
    case 'OPEN_DASHBOARD': {
      const tabTarget = message.tab ? `?tab=${message.tab}` : '';
      const url = chrome.runtime.getURL(`dashboard/dashboard.html${tabTarget}`);
      chrome.tabs.create({ url });
      return { success: true };
    }

    // 16. Update Configuration
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
