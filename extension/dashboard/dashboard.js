/**
 * StudyMate AI – Dashboard Controller
 * Connects frontend views to background service worker and backend API.
 */

document.addEventListener('DOMContentLoaded', () => {
    let currentTasks = [];
    let currentFilter = 'all';
    let selectedStudyAction = 'explain';
    let activeEditor = null;

    const els = {
        navLinks: document.querySelectorAll('.nav-link'),
        tabContents: document.querySelectorAll('.tab-content'),
        pageTitle: document.getElementById('pageTitle'),
        refreshBtn: document.getElementById('refreshBtn'),
        recentGrid: document.getElementById('recentTasksGrid'),
        allTasksGrid: document.getElementById('allTasksGrid'),
        draftsGrid: document.getElementById('draftsGrid'),
        solutionEditorContainer: document.getElementById('solutionEditorContainer'),
        filterBtns: document.querySelectorAll('.filter-btn'),
        pendingOverviewCount: document.getElementById('pendingOverviewCount'),
        draftOverviewCount: document.getElementById('draftOverviewCount'),
        submittedOverviewCount: document.getElementById('submittedOverviewCount'),
        totalOverviewCount: document.getElementById('totalOverviewCount'),
        studyToolCards: document.querySelectorAll('.study-tool-card'),
        studyToolHeader: document.getElementById('studyToolHeader'),
        studyTopicInput: document.getElementById('studyTopicInput'),
        runStudyToolBtn: document.getElementById('runStudyToolBtn'),
        studyResultContainer: document.getElementById('studyResultContainer'),
        studyResultText: document.getElementById('studyResultText'),
        historyList: document.getElementById('historyList'),
        settingsAiProvider: document.getElementById('settingsAiProvider'),
        settingsAiModel: document.getElementById('settingsAiModel'),
        settingsAiApiKey: document.getElementById('settingsAiApiKey'),
        settingsApiUrl: document.getElementById('settingsApiUrl'),
        settingsMoodleUrl: document.getElementById('settingsMoodleUrl'),
        settingsAutoSubmit: document.getElementById('settingsAutoSubmit'),
        settingsAutoScan: document.getElementById('settingsAutoScan'),
        saveSettingsBtn: document.getElementById('saveSettingsBtn')
    };

    // Navigation Tab Switching
    els.navLinks.forEach(link => {
        link.addEventListener('click', () => {
            const target = link.getAttribute('data-target');
            switchTab(target);
        });
    });

    function switchTab(tabId) {
        els.navLinks.forEach(l => {
            if (l.getAttribute('data-target') === tabId) l.classList.add('active');
            else l.classList.remove('active');
        });

        els.tabContents.forEach(t => {
            if (t.id === tabId) t.classList.add('active');
            else t.classList.remove('active');
        });

        const titles = {
            'overview': 'Dashboard Overview',
            'tasks': 'All Academic Tasks',
            'review': 'Review & Edit AI Solutions',
            'study': 'AI Academic Study Tools',
            'history': 'Submission & Task History',
            'settings': 'Settings & LMS Configuration'
        };
        if (els.pageTitle) {
            els.pageTitle.textContent = titles[tabId] || 'Dashboard';
        }

        if (tabId === 'history') {
            loadHistory();
        } else if (tabId === 'settings') {
            loadSettings();
        }
    }

    // Task Filter Buttons
    els.filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            els.filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.getAttribute('data-filter');
            renderAllTasksGrid();
        });
    });

    // Refresh Data Button
    els.refreshBtn.addEventListener('click', () => {
        StudyMateNotification.info('Refreshing tasks from LMS & backend...');
        loadTasks();
    });

    // Load Tasks from Background / Backend
    async function loadTasks() {
        try {
            const res = await chrome.runtime.sendMessage({ type: 'GET_TASKS' });
            if (res && res.success && Array.isArray(res.tasks)) {
                currentTasks = res.tasks;
            } else if (res && Array.isArray(res.tasks)) {
                currentTasks = res.tasks;
            } else {
                currentTasks = [];
            }
            updateStatsAndGrids();
        } catch (e) {
            console.error('Error loading tasks:', e);
            StudyMateNotification.error('Failed to load tasks. Backend might be offline.');
        }
    }

    function updateStatsAndGrids() {
        // Update stats
        const pending = currentTasks.filter(t => t.status === 'PENDING' || t.status === 'Pending' || t.status === 'DISCOVERED');
        const drafts = currentTasks.filter(t => t.status === 'GENERATED' || t.status === 'Draft Ready' || t.status === 'REVIEW' || t.status === 'In Draft');
        const submitted = currentTasks.filter(t => t.status === 'SUBMITTED' || t.status === 'Submitted' || t.status === 'COMPLETED');

        if (els.pendingOverviewCount) els.pendingOverviewCount.textContent = pending.length;
        if (els.draftOverviewCount) els.draftOverviewCount.textContent = drafts.length;
        if (els.submittedOverviewCount) els.submittedOverviewCount.textContent = submitted.length;
        if (els.totalOverviewCount) els.totalOverviewCount.textContent = currentTasks.length;

        // Render Recent Tasks Grid (Overview)
        renderRecentGrid();
        // Render All Tasks Grid
        renderAllTasksGrid();
        // Render Drafts / Review Grid
        renderDraftsGrid();
    }

    function renderRecentGrid() {
        if (!els.recentGrid) return;
        els.recentGrid.innerHTML = '';
        if (currentTasks.length === 0) {
            els.recentGrid.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">📚</div>
                    <div class="empty-state__title">No tasks detected yet</div>
                    <div class="empty-state__desc">Navigate to a Moodle assignment or quiz page and click "Scan for Assignments".</div>
                </div>`;
            return;
        }

        const recent = currentTasks.slice(0, 4);
        recent.forEach(task => {
            const card = TaskCard.create(task, {
                showActions: true,
                onSolve: (t) => handleSolveTask(t),
                onView: (t) => openTaskInReview(t)
            });
            els.recentGrid.appendChild(card);
        });
    }

    function renderAllTasksGrid() {
        if (!els.allTasksGrid) return;
        els.allTasksGrid.innerHTML = '';

        let filtered = currentTasks;
        if (currentFilter !== 'all') {
            filtered = currentTasks.filter(t => (t.type || 'ASSIGNMENT').toUpperCase() === currentFilter.toUpperCase());
        }

        if (filtered.length === 0) {
            els.allTasksGrid.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">🔍</div>
                    <div class="empty-state__title">No ${currentFilter === 'all' ? '' : currentFilter.toLowerCase()} tasks found</div>
                    <div class="empty-state__desc">Scan Moodle to discover assignments and quizzes.</div>
                </div>`;
            return;
        }

        filtered.forEach(task => {
            const card = TaskCard.create(task, {
                showActions: true,
                onSolve: (t) => handleSolveTask(t),
                onView: (t) => openTaskInReview(t)
            });
            els.allTasksGrid.appendChild(card);
        });
    }

    function renderDraftsGrid() {
        if (!els.draftsGrid) return;
        els.draftsGrid.innerHTML = '';

        const reviewable = currentTasks.filter(t =>
            t.status === 'GENERATED' || t.status === 'Draft Ready' ||
            t.status === 'REVIEW' || t.status === 'In Draft' ||
            t.status === 'APPROVED' || t.solution
        );

        if (reviewable.length === 0) {
            els.draftsGrid.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">📝</div>
                    <div class="empty-state__title">No drafts ready for review</div>
                    <div class="empty-state__desc">Click "Solve with AI" on any task to generate a solution draft.</div>
                </div>`;
            return;
        }

        reviewable.forEach(task => {
            const card = TaskCard.create(task, {
                showActions: true,
                onSolve: (t) => handleSolveTask(t),
                onView: (t) => openTaskInReview(t)
            });
            els.draftsGrid.appendChild(card);
        });
    }

    async function handleSolveTask(task) {
        const config = await getConfig();
        const providerName = config.aiProvider ? config.aiProvider.toUpperCase() : 'AI';
        StudyMateNotification.info(`Generating AI solution for "${task.title || 'Task'}" using ${providerName}...`);
        try {
            const res = await chrome.runtime.sendMessage({
                type: 'GENERATE_AI_SOLUTION',
                payload: {
                    taskId: task.id || task.task_id,
                    task_id: task.id || task.task_id,
                    prompt: task.custom_prompt || '',
                    context: task.description || '',
                    provider: config.aiProvider,
                    model: config.aiModel,
                    api_key: config.aiApiKey
                }
            });

            if (res && res.success) {
                StudyMateNotification.success('Solution generated successfully! Opening in Review tab.');
                await loadTasks();
                const updatedTask = currentTasks.find(t => (t.id || t.task_id) == (task.id || task.task_id)) || task;
                if (res.solution) {
                    updatedTask.solution = res.solution;
                }
                openTaskInReview(updatedTask);
            } else {
                StudyMateNotification.error(res?.error || 'Failed to generate solution.');
            }
        } catch (e) {
            console.error('Error generating solution:', e);
            StudyMateNotification.error('Error contacting AI service.');
        }
    }

    // Open Task in Review / Answer Editor
    function openTaskInReview(task) {
        switchTab('review');
        if (!els.solutionEditorContainer) return;

        const solution = task.solution || {
            solution_id: task.solution_id,
            generated_answer: task.generated_answer || 'No generated solution found. Click "Regenerate" to create one.',
            edited_answer: task.edited_answer,
            status: task.status || 'GENERATED'
        };

        activeEditor = new AnswerEditor(els.solutionEditorContainer, {
            task: task,
            solution: solution,
            onSave: async (t, editedText) => {
                await chrome.runtime.sendMessage({
                    type: 'SAVE_DRAFT_SOLUTION',
                    payload: {
                        task_id: t.id || t.task_id,
                        solution_id: solution.solution_id || solution.id,
                        edited_answer: editedText
                    }
                });
                await loadTasks();
            },
            onApprove: async (t, approvedText) => {
                await chrome.runtime.sendMessage({
                    type: 'SAVE_DRAFT_SOLUTION',
                    payload: {
                        task_id: t.id || t.task_id,
                        solution_id: solution.solution_id || solution.id,
                        edited_answer: approvedText,
                        status: 'APPROVED'
                    }
                });
                await loadTasks();
            },
            onRegenerate: async (t) => {
                await handleSolveTask(t);
            },
            onSubmit: async (t, sol) => {
                StudyMateNotification.info('Submitting solution to Moodle...');
                try {
                    const res = await chrome.runtime.sendMessage({
                        type: 'SUBMIT_SOLUTION',
                        payload: {
                            task_id: t.id || t.task_id,
                            solution_id: sol.solution_id || sol.id
                        }
                    });
                    if (res && res.success) {
                        StudyMateNotification.success('Task successfully submitted to Moodle!');
                        await loadTasks();
                        openTaskInReview(t);
                    } else {
                        StudyMateNotification.error(res?.error || 'Submission failed.');
                    }
                } catch (e) {
                    StudyMateNotification.error('Error during submission.');
                }
            }
        });
    }

    // Study Tools
    els.studyToolCards.forEach(card => {
        card.addEventListener('click', () => {
            els.studyToolCards.forEach(c => c.style.borderColor = 'var(--border)');
            card.style.borderColor = 'var(--primary)';
            selectedStudyAction = card.getAttribute('data-action');
            
            const titles = {
                'explain': 'Explain Concept (Step-by-step)',
                'summarize': 'Summarize Topic & Key Points',
                'notes': 'Generate Structured Study Notes',
                'practice': 'Generate Practice Questions & Solutions'
            };
            if (els.studyToolHeader) {
                els.studyToolHeader.textContent = titles[selectedStudyAction] || 'Enter Topic or Question';
            }
        });
    });

    if (els.runStudyToolBtn) {
        els.runStudyToolBtn.addEventListener('click', async () => {
            const topic = els.studyTopicInput ? els.studyTopicInput.value.trim() : '';
            if (!topic) {
                StudyMateNotification.warning('Please enter a topic or concept to study.');
                return;
            }

            StudyMateNotification.info(`Generating ${selectedStudyAction} for "${topic}"...`);
            els.runStudyToolBtn.disabled = true;

            try {
                const config = await getConfig();
                const res = await fetch(`${config.backendUrl}/study/${selectedStudyAction}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        topic: topic,
                        provider: config.aiProvider,
                        model: config.aiModel,
                        api_key: config.aiApiKey
                    })
                });
                const data = await res.json();

                if (data && (data.material || data.result)) {
                    if (els.studyResultContainer) els.studyResultContainer.style.display = 'block';
                    if (els.studyResultText) els.studyResultText.textContent = data.material || data.result;
                    StudyMateNotification.success(`Study material generated via ${data.provider || config.aiProvider || 'AI'}!`);
                } else {
                    StudyMateNotification.error(data?.error || 'Failed to generate study material.');
                }
            } catch (e) {
                console.error('Study tool error:', e);
                StudyMateNotification.error('Failed to communicate with StudyMate AI service.');
            } finally {
                els.runStudyToolBtn.disabled = false;
            }
        });
    }

    // Task History
    async function loadHistory() {
        if (!els.historyList) return;
        els.historyList.innerHTML = '<p>Loading history...</p>';

        const storage = await chrome.storage.local.get(['history', 'tasks']);
        const history = storage.history || [];

        if (history.length === 0) {
            els.historyList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">📜</div>
                    <div class="empty-state__title">No submission history yet</div>
                    <div class="empty-state__desc">Completed submissions and actions will be logged here.</div>
                </div>`;
            return;
        }

        els.historyList.innerHTML = '';
        history.slice().reverse().forEach(item => {
            const div = document.createElement('div');
            div.className = 'history-item';
            div.innerHTML = `
                <div class="history-item__info">
                    <div class="history-item__title">${item.title || 'Task Action'}</div>
                    <div class="history-item__meta">
                        ${item.type || 'Action'} • ${item.status || 'Completed'} • ${item.timestamp ? new Date(item.timestamp).toLocaleString() : 'Recent'}
                    </div>
                </div>
                <span class="task-card__badge badge--completed">✓ Completed</span>
            `;
            els.historyList.appendChild(div);
        });
    }

    // Provider Model Placeholders
    const PROVIDER_PLACEHOLDERS = {
        'google': 'e.g. gemini-1.5-flash, gemini-2.0-flash, gemini-1.5-pro',
        'claude': 'e.g. claude-3-5-sonnet-20241022, claude-3-5-haiku-20241022, claude-3-7-sonnet-20250219',
        'groq': 'e.g. llama-3.3-70b-versatile, llama-3.1-8b-instant, mixtral-8x7b-32768',
        'openai': 'e.g. gpt-4o, gpt-4o-mini, gpt-4-turbo, o1, o3-mini',
        'deepseek': 'e.g. deepseek-chat, deepseek-reasoner',
        'ollama': 'e.g. llama3, llama3.1, mistral, qwen2.5, phi3, deepseek-r1',
        'fallback': 'Offline template mode (no model required)'
    };

    if (els.settingsAiProvider) {
        els.settingsAiProvider.addEventListener('change', () => {
            const selected = els.settingsAiProvider.value;
            if (els.settingsAiModel) {
                els.settingsAiModel.placeholder = PROVIDER_PLACEHOLDERS[selected] || 'Enter custom model name';
            }
        });
    }

    // Settings
    async function loadSettings() {
        const config = await getConfig();
        if (els.settingsAiProvider) els.settingsAiProvider.value = config.aiProvider || 'google';
        if (els.settingsAiModel) els.settingsAiModel.value = config.aiModel || '';
        if (els.settingsAiApiKey) els.settingsAiApiKey.value = config.aiApiKey || '';
        if (els.settingsApiUrl) els.settingsApiUrl.value = config.backendUrl || 'http://localhost:5000/api';
        if (els.settingsMoodleUrl) els.settingsMoodleUrl.value = config.moodleUrl || 'http://moodle.local';
        if (els.settingsAutoSubmit) els.settingsAutoSubmit.checked = !!config.autoSubmit;
        if (els.settingsAutoScan) els.settingsAutoScan.checked = config.autoScan !== false;

        // Set placeholder based on initial provider
        if (els.settingsAiProvider && els.settingsAiModel) {
            const currentProvider = els.settingsAiProvider.value;
            els.settingsAiModel.placeholder = PROVIDER_PLACEHOLDERS[currentProvider] || 'e.g. gemini-1.5-flash';
        }

        // Fetch backend provider details to enrich provider selector
        try {
            const res = await chrome.runtime.sendMessage({ type: 'GET_AI_PROVIDERS' });
            if (res && res.success && Array.isArray(res.providers) && els.settingsAiProvider) {
                const currentVal = config.aiProvider || res.active_provider || 'google';
                els.settingsAiProvider.innerHTML = '';

                res.providers.forEach(p => {
                    const opt = document.createElement('option');
                    opt.value = p.id;
                    const statusTag = p.configured ? ' ✓ (Configured in .env)' : '';
                    opt.textContent = `${p.name} [Default: ${p.default_model}]${statusTag}`;
                    if (p.id === currentVal) opt.selected = true;
                    els.settingsAiProvider.appendChild(opt);
                });

                const fallbackOpt = document.createElement('option');
                fallbackOpt.value = 'fallback';
                fallbackOpt.textContent = 'Local Academic Fallback (Offline Demo Mode)';
                if (currentVal === 'fallback') fallbackOpt.selected = true;
                els.settingsAiProvider.appendChild(fallbackOpt);
            }
        } catch (e) {
            console.log('[StudyMate AI] Live provider list unavailable; using static list.');
        }
    }

    if (els.saveSettingsBtn) {
        els.saveSettingsBtn.addEventListener('click', async () => {
            const newConfig = {
                aiProvider: els.settingsAiProvider ? els.settingsAiProvider.value : 'google',
                aiModel: els.settingsAiModel ? els.settingsAiModel.value.trim() : '',
                aiApiKey: els.settingsAiApiKey ? els.settingsAiApiKey.value.trim() : '',
                backendUrl: els.settingsApiUrl ? els.settingsApiUrl.value.trim() : 'http://localhost:5000/api',
                moodleUrl: els.settingsMoodleUrl ? els.settingsMoodleUrl.value.trim() : 'http://moodle.local',
                autoSubmit: els.settingsAutoSubmit ? els.settingsAutoSubmit.checked : false,
                autoScan: els.settingsAutoScan ? els.settingsAutoScan.checked : true
            };

            await chrome.runtime.sendMessage({
                type: 'UPDATE_CONFIG',
                payload: newConfig
            });

            StudyMateNotification.success('Settings & AI Provider saved successfully!');
        });
    }

    async function getConfig() {
        const stored = await chrome.storage.local.get(['config']);
        return stored.config || { backendUrl: 'http://localhost:5000/api', moodleUrl: 'http://moodle.local', aiProvider: 'google' };
    }

    // Initial Load
    loadTasks();
});
