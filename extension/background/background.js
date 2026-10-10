/**
 * StudyMate AI - Background Service Worker
 * Manages communication between Content Scripts, Popup UI, Dashboard, Chrome Storage, and Python Backend API.
 */

const DEFAULT_CONFIG = {
  backendUrl: 'http://localhost:5000/api',
  moodleUrl: 'http://moodle.local',
  aiProvider: 'groq', // 'groq' | 'google' | 'claude' | 'openai' | 'deepseek' | 'ollama' | 'fallback'
  aiModel: 'openai/gpt-oss-120b',
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
      console.log('[StudyMate AI] Scanned task context received:', task);

      const storage = await chrome.storage.local.get(['tasks']);
      const tasks = storage.tasks || [];
      const taskId = task.id || task.task_id || task.moodle_activity_id;
      const existingIdx = tasks.findIndex(t =>
        (t.id || t.task_id) === taskId ||
        (t.moodle_activity_id && task.moodle_activity_id && t.moodle_activity_id === task.moodle_activity_id) ||
        (t.title === task.title && (t.course || t.courseName) === (task.course || task.courseName))
      );

      // Only update verified existing tasks; do not inject phantom DOM links
      if (existingIdx >= 0) {
        tasks[existingIdx] = {
          ...tasks[existingIdx],
          ...task,
          updatedAt: new Date().toISOString()
        };
        await chrome.storage.local.set({ tasks });

        const backendRes = await apiRequest('/tasks/sync', {
          method: 'POST',
          body: JSON.stringify({ task })
        });

        return { success: true, localTasks: tasks, backendSynced: backendRes.success };
      }

      return { success: true, localTasks: tasks, backendSynced: false, ignoredUnverified: true };
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
      const queryParts = ['enrolled_only=true'];
      if (message.pendingOnly) queryParts.push('pending_only=true');
      const backendRes = await apiRequest(`/tasks?${queryParts.join('&')}`);
      if (backendRes.success && Array.isArray(backendRes.tasks)) {
        await chrome.storage.local.set({ tasks: backendRes.tasks });
        return { success: true, tasks: backendRes.tasks, source: 'backend' };
      }
      // Fallback to local storage (exclude unavailable tasks)
      const stored = await chrome.storage.local.get(['tasks']);
      let localTasks = stored.tasks || [];
      localTasks = localTasks.filter(t => t.availabilityStatus !== 'UNAVAILABLE' && t.availability_status !== 'UNAVAILABLE');
      if (message.pendingOnly) {
        localTasks = localTasks.filter(t => (t.isActionablePending === 1 || t.isActionablePending === true || t.is_actionable_pending === 1) && t.availabilityStatus !== 'SUBMITTED' && t.availability_status !== 'SUBMITTED' && t.status !== 'Submitted' && t.status !== 'SUBMITTED' && t.status !== 'COMPLETED');
      }
      return { success: true, tasks: localTasks, source: 'local' };
    }

    // 7. Get Learning Resources
    case 'GET_RESOURCES': {
      const queryParts = ['enrolled_only=true'];
      if (message.courseId) queryParts.push(`course_id=${message.courseId}`);
      const backendRes = await apiRequest(`/resources?${queryParts.join('&')}`);
      if (backendRes.success && Array.isArray(backendRes.resources)) {
        await chrome.storage.local.set({ resources: backendRes.resources });
        return {
          success: true,
          resources: backendRes.resources,
          courses: backendRes.courses || [],
          source: 'backend'
        };
      }
      // Fallback to local storage (filter out unavailable)
      const stored = await chrome.storage.local.get(['resources']);
      let localRes = stored.resources || [];
      localRes = localRes.filter(r => r.availability_status !== 'UNAVAILABLE' && r.availabilityStatus !== 'UNAVAILABLE');
      return { success: true, resources: localRes, source: 'local' };
    }

    // 8. Generate AI Solution
    case 'GENERATE_AI_SOLUTION': {
      const config = await getConfig();
      const payload = message.payload || {};
      const taskId = payload.task_id || payload.taskId;
      const prompt = payload.prompt || payload.custom_prompt || '';
      const context = payload.context || '';
      const provider = payload.provider || config.aiProvider || 'groq';
      const model = payload.model || config.aiModel || 'openai/gpt-oss-120b';
      const apiKey = payload.api_key || config.aiApiKey || '';
      const shouldAutoSubmit = payload.autoSubmit !== undefined ? payload.autoSubmit : (payload.auto_submit !== undefined ? payload.auto_submit : !!config.autoSubmit);

      console.log(`[StudyMate AI] Requesting AI solution for task ${taskId} using ${provider}... (autoSubmit: ${shouldAutoSubmit})`);

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

        // Auto-upload and submit to Moodle if autoSubmit is enabled
        if (shouldAutoSubmit) {
          console.log(`[StudyMate AI] autoSubmit is enabled. Uploading generated solution directly to Moodle...`);
          try {
            const solText = backendRes.solution?.generated_answer || backendRes.solution?.edited_answer || backendRes.answer || '';
            const uploadRes = await apiRequest('/submissions/upload-to-moodle', {
              method: 'POST',
              body: JSON.stringify({
                task_id: taskId,
                solution_id: backendRes.solution_id,
                format: 'DOCX',
                answer: solText
              })
            });

            if (uploadRes.success) {
              backendRes.autoSubmitted = true;
              backendRes.submission_status = uploadRes.submission_status;
              backendRes.file_name = uploadRes.file_name;

              // Update local task to Submitted
              const postStorage = await chrome.storage.local.get(['tasks', 'history']);
              const pTasks = postStorage.tasks || [];
              const pIdx = pTasks.findIndex(t => (t.id || t.task_id) == taskId);
              if (pIdx >= 0) {
                pTasks[pIdx].status = 'Submitted';
                pTasks[pIdx].availabilityStatus = 'SUBMITTED';
                pTasks[pIdx].isActionablePending = false;
                pTasks[pIdx].submissionStatus = uploadRes.submission_status || 'Submitted for grading';
                await chrome.storage.local.set({ tasks: pTasks });
              }

              // Record in submission history
              const history = postStorage.history || [];
              history.unshift({
                id: 'sub_' + Date.now(),
                taskId: taskId,
                title: tasks[tIdx]?.title || 'Assignment Submission',
                course: tasks[tIdx]?.courseName || tasks[tIdx]?.course || 'Course',
                submittedAt: new Date().toISOString(),
                fileName: uploadRes.file_name,
                fileFormat: 'DOCX',
                status: uploadRes.submission_status || 'Submitted for grading',
                verified: true
              });
              await chrome.storage.local.set({ history });
            }
          } catch (autoErr) {
            console.error('[StudyMate AI] Auto-submission error:', autoErr);
          }
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
      const fileFormat = (payload.format || payload.file_format || 'DOCX').toUpperCase();
      const answer = payload.answer || payload.edited_answer || '';
      let targetTabId = payload.tabId;

      console.log(`[StudyMate AI] Uploading & Submitting task ${taskId} to Moodle via Web Services API...`);

      // Call backend direct Moodle Web Services upload endpoint
      const uploadRes = await apiRequest('/submissions/upload-to-moodle', {
        method: 'POST',
        body: JSON.stringify({
          task_id: taskId,
          solution_id: solutionId,
          format: fileFormat,
          answer: answer
        })
      });

      if (!uploadRes.success) {
        console.error('[StudyMate AI] Moodle upload failed:', uploadRes);
        return {
          success: false,
          error: uploadRes.error || 'Failed to upload assignment to Moodle LMS.',
          errorcode: uploadRes.errorcode
        };
      }

      // Update local storage tasks
      const storage = await chrome.storage.local.get(['tasks', 'history']);
      const tasks = storage.tasks || [];
      const tIdx = tasks.findIndex(t => (t.id || t.task_id) == taskId);
      let taskTitle = 'Assignment Submission';
      let courseName = 'Course';

      if (tIdx >= 0) {
        taskTitle = tasks[tIdx].title || taskTitle;
        courseName = tasks[tIdx].courseName || tasks[tIdx].course || courseName;
        tasks[tIdx].status = 'Submitted';
        tasks[tIdx].availabilityStatus = 'SUBMITTED';
        tasks[tIdx].isActionablePending = false;
        tasks[tIdx].submissionStatus = uploadRes.submission_status || 'Submitted for grading';
        await chrome.storage.local.set({ tasks });
      }

      // Log to history
      const history = storage.history || [];
      history.unshift({
        id: 'sub_' + Date.now(),
        taskId: taskId,
        title: taskTitle,
        course: courseName,
        submittedAt: new Date().toISOString(),
        fileName: uploadRes.file_name,
        fileFormat: fileFormat,
        status: uploadRes.submission_status || 'Submitted for grading',
        verified: true
      });
      await chrome.storage.local.set({ history });

      // Open or focus the Moodle assignment tab so the student can see their confirmed submission
      const moodleUrl = uploadRes.moodle_url || payload.moodle_url;
      if (moodleUrl) {
        try {
          const tabs = await chrome.tabs.query({});
          const moodleTab = tabs.find(t => t.url && (t.url.includes('mod/assign') || t.url.includes('moodle.local')));
          if (moodleTab) {
            await chrome.tabs.update(moodleTab.id, { url: moodleUrl, active: true });
          } else {
            await chrome.tabs.create({ url: moodleUrl });
          }
        } catch (tabErr) {
          console.warn('[StudyMate AI] Could not open/update Moodle tab:', tabErr);
        }
      }

      return {
        success: true,
        file_name: uploadRes.file_name,
        fileName: uploadRes.file_name,
        submission_status: uploadRes.submission_status,
        is_submitted: uploadRes.is_submitted,
        moodle_url: moodleUrl,
        message: uploadRes.message || 'Successfully uploaded and submitted to Moodle!'
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
