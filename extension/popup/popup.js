/**
 * StudyMate AI – Popup Controller
 * Manages the extension popup UI, live stats, Moodle detection status, and quick scan actions.
 * Only displays verified actionable pending assignments.
 */

document.addEventListener('DOMContentLoaded', async () => {
    const scanBtn = document.getElementById('scanBtn');
    const settingsBtn = document.getElementById('openSettingsBtn');
    const viewAllBtn = document.getElementById('viewAllBtn');
    const autoSubmitToggle = document.getElementById('autoSubmitToggle');
    const navItems = document.querySelectorAll('.nav-item');
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');
    const aiCard = document.getElementById('aiAgentCard');
    const aiStatusTitle = document.getElementById('aiStatusTitle');
    const aiStatusDesc = document.getElementById('aiStatusDesc');
    const aiPulse = document.getElementById('aiPulse');
    const taskList = document.getElementById('popupTaskList');

    const statPending = document.getElementById('statPending');
    const statDraft = document.getElementById('statDraft');
    const statSubmitted = document.getElementById('statSubmitted');

    // Load initial data from Storage & Background
    await initPopup();

    async function initPopup() {
        const storage = await chrome.storage.local.get(['config', 'tasks', 'resources', 'history', 'currentPage']);
        const config = storage.config || { autoSubmit: false };
        const tasks = storage.tasks || [];

        // 1. Sync Toggle
        if (autoSubmitToggle) {
            autoSubmitToggle.checked = !!config.autoSubmit;
        }

        // 2. Render Live Stats & Verified Actionable Tasks
        renderStatsAndTasks(tasks);

        // 3. Check Current Active Tab for Moodle
        try {
            const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
            if (tabs[0] && tabs[0].url) {
                const url = tabs[0].url;
                const isMoodle = url.includes('moodle') || url.includes('localhost') || url.includes('127.0.0.1');
                if (isMoodle) {
                    if (storage.currentPage && storage.currentPage.type && storage.currentPage.type !== 'NONE') {
                        updateConnectionStatus(true, `Active on Moodle: ${storage.currentPage.type}`);
                    } else {
                        updateConnectionStatus(true, 'Connected to Moodle Portal');
                    }
                } else {
                    updateConnectionStatus(false, 'Not on a Moodle page');
                }
            }
        } catch (e) {
            console.error('Tab query error:', e);
        }

        // 4. Verify Backend Health & AI Status
        try {
            const health = await chrome.runtime.sendMessage({ type: 'CHECK_BACKEND_HEALTH' });
            if (!health || health.status !== 'ok') {
                setAIOffline();
            } else {
                const activeProvider = config.aiProvider || health.ai_provider || 'google';
                const activeModel = config.aiModel || health.ai_model || '';
                setAIOnline(activeProvider, activeModel);
            }
        } catch (e) {
            setAIOffline();
        }
    }

    function renderStatsAndTasks(tasks) {
        // Strict Category 1 pending filter: must be verified available and actionable
        const pending = tasks.filter(t =>
            (t.is_actionable_pending === 1 || t.isActionablePending === true || t.availability_status === 'AVAILABLE' || t.availabilityStatus === 'AVAILABLE') &&
            t.status !== 'SUBMITTED' && t.status !== 'Submitted' && t.status !== 'COMPLETED' && t.status !== 'Closed' && t.status !== 'Unavailable'
        );
        const drafts = tasks.filter(t => t.status === 'GENERATED' || t.status === 'Draft Ready' || t.status === 'REVIEW' || t.status === 'In Draft');
        const submitted = tasks.filter(t => t.status === 'SUBMITTED' || t.status === 'Submitted' || t.status === 'COMPLETED');

        if (statPending) statPending.textContent = String(pending.length).padStart(2, '0');
        if (statDraft) statDraft.textContent = String(drafts.length).padStart(2, '0');
        if (statSubmitted) statSubmitted.textContent = String(submitted.length).padStart(2, '0');

        if (!taskList) return;
        taskList.innerHTML = '';

        if (pending.length === 0) {
            taskList.innerHTML = `
                <div style="text-align: center; padding: 24px 12px; color: var(--text-secondary); font-size: 13px;">
                    <p style="font-size: 24px; margin-bottom: 6px;">📚</p>
                    <p style="font-weight: 500;">No pending assignments are currently available in your Moodle courses.</p>
                    <p style="font-size: 11px; margin-top: 4px; opacity: 0.8;">Click "Scan for Assignments" to inspect the current page.</p>
                </div>
            `;
            return;
        }

        const previewTasks = pending.slice(0, 3);
        previewTasks.forEach(task => {
            const item = document.createElement('div');
            item.className = 'task';
            item.style.cursor = 'pointer';

            const isQuiz = (task.type === 'QUIZ');
            const statusClass = getBadgeClass(task.status);
            const statusLabel = getBadgeLabel(task.status);

            item.innerHTML = `
                <div class="task-icon ${isQuiz ? 'quiz' : 'assignment'}">
                    ${isQuiz ? `
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="10"/>
                            <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
                            <line x1="12" y1="17" x2="12.01" y2="17"/>
                        </svg>
                    ` : `
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                            <polyline points="14 2 14 8 20 8"/>
                            <line x1="16" y1="13" x2="8" y2="13"/>
                            <line x1="16" y1="17" x2="8" y2="17"/>
                        </svg>
                    `}
                </div>
                <div class="task-info">
                    <h4>${escapeHtml(task.title || 'Untitled Task')}</h4>
                    <p>${task.due_date || task.dueDate || task.course || 'No due date'}</p>
                </div>
                <span class="badge ${statusClass}">${statusLabel}</span>
                <span class="arrow">›</span>
            `;

            item.addEventListener('click', () => {
                chrome.runtime.sendMessage({ type: 'OPEN_DASHBOARD', tab: 'review' });
            });

            taskList.appendChild(item);
        });
    }

    function getBadgeClass(status) {
        if (status === 'Draft Ready' || status === 'GENERATED' || status === 'APPROVED') return 'badge-draft';
        if (status === 'SUBMITTED' || status === 'COMPLETED') return 'badge-draft';
        if (status === 'PROCESSING' || status === 'Processing') return 'badge-processing';
        return 'badge-pending';
    }

    function getBadgeLabel(status) {
        if (status === 'GENERATED' || status === 'Draft Ready') return 'Draft Ready';
        if (status === 'APPROVED') return 'Approved';
        if (status === 'SUBMITTED') return 'Submitted';
        if (status === 'PROCESSING') return 'Processing';
        return 'Pending';
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function updateConnectionStatus(isConnected, text) {
        if (!statusDot || !statusText) return;
        if (isConnected) {
            statusDot.className = 'status-dot connected';
            statusText.textContent = text;
            statusText.style.color = 'var(--text-secondary)';
        } else {
            statusDot.className = 'status-dot';
            statusDot.style.background = '#ffa502';
            statusDot.style.boxShadow = 'none';
            statusText.textContent = text;
            statusText.style.color = '#ffa502';
        }
    }

    function setAIOffline() {
        if (!aiCard) return;
        aiCard.style.opacity = '0.6';
        if (aiStatusTitle) aiStatusTitle.textContent = 'AI Agent Offline';
        if (aiStatusDesc) aiStatusDesc.textContent = 'Backend server not detected (Run app.py)';
        if (aiPulse) aiPulse.style.display = 'none';
    }

    function setAIOnline(provider, model) {
        if (!aiCard) return;
        aiCard.style.opacity = '1';
        aiCard.style.cursor = 'pointer';
        aiCard.title = 'Click to configure AI providers in Dashboard';
        if (aiStatusTitle) aiStatusTitle.textContent = 'AI Agent Active';

        const providerDisplayMap = {
            'google': 'Google Gemini',
            'claude': 'Anthropic Claude',
            'groq': 'Groq Cloud',
            'openai': 'OpenAI GPT',
            'deepseek': 'DeepSeek',
            'ollama': 'Ollama Local',
            'fallback': 'Local Fallback'
        };
        const pName = providerDisplayMap[(provider || '').toLowerCase()] || (provider ? provider.toUpperCase() : 'AI Active');
        const mName = model ? ` • ${model}` : '';
        if (aiStatusDesc) aiStatusDesc.textContent = `Ready (${pName}${mName})`;
        if (aiPulse) aiPulse.style.display = 'block';
    }

    if (aiCard) {
        aiCard.addEventListener('click', () => {
            chrome.runtime.sendMessage({ type: 'OPEN_DASHBOARD' });
        });
    }

    // Scan Button Handler
    if (scanBtn) {
        scanBtn.addEventListener('click', async () => {
            scanBtn.disabled = true;
            scanBtn.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin">
                    <line x1="12" y1="2" x2="12" y2="6"/>
                    <line x1="12" y1="18" x2="12" y2="22"/>
                    <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/>
                    <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/>
                    <line x1="2" y1="12" x2="6" y2="12"/>
                    <line x1="18" y1="12" x2="22" y2="12"/>
                    <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"/>
                    <line x1="16.24" y1="7.76" x2="19.07" y2="4.93"/>
                </svg>
                Scanning page...
            `;

            try {
                const res = await chrome.runtime.sendMessage({ type: 'TRIGGER_ACTIVE_TAB_SCAN' });
                if (res && res.success) {
                    scanBtn.innerHTML = '✓ Scan Complete';
                    scanBtn.style.background = 'var(--accent-green)';
                    await initPopup();
                } else {
                    scanBtn.innerHTML = res?.error || '! Scan Complete';
                }
            } catch (e) {
                console.error(e);
                scanBtn.innerHTML = '! Scan Failed';
            }

            setTimeout(() => {
                scanBtn.disabled = false;
                scanBtn.style.background = '';
                scanBtn.innerHTML = `
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                         stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="23 4 23 10 17 10"/>
                        <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
                    </svg>
                    Scan for Assignments
                `;
            }, 2500);
        });
    }

    // Auto-Submit Toggle Handler
    if (autoSubmitToggle) {
        autoSubmitToggle.addEventListener('change', async (e) => {
            const isChecked = e.target.checked;
            await chrome.runtime.sendMessage({
                type: 'UPDATE_CONFIG',
                payload: { autoSubmit: isChecked }
            });
        });
    }

    // Dashboard navigation buttons
    if (settingsBtn) {
        settingsBtn.addEventListener('click', () => {
            chrome.runtime.sendMessage({ type: 'OPEN_DASHBOARD', tab: 'settings' });
        });
    }

    if (viewAllBtn) {
        viewAllBtn.addEventListener('click', () => {
            chrome.runtime.sendMessage({ type: 'OPEN_DASHBOARD', tab: 'tasks' });
        });
    }

    // Bottom Navigation Handlers
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            navItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            const tab = item.getAttribute('data-tab');
            if (tab === 'tasks') {
                chrome.runtime.sendMessage({ type: 'OPEN_DASHBOARD', tab: 'tasks' });
            } else if (tab === 'agent') {
                chrome.runtime.sendMessage({ type: 'OPEN_DASHBOARD', tab: 'study' });
            } else if (tab === 'history') {
                chrome.runtime.sendMessage({ type: 'OPEN_DASHBOARD', tab: 'history' });
            }
        });
    });
});
