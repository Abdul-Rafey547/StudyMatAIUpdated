/**
 * StudyMate AI – Dashboard Controller
 * Connects frontend views to background service worker and backend API.
 * Manages tasks, study materials, AI review editor, and study workbench.
 */

document.addEventListener('DOMContentLoaded', () => {
    let currentTasks = [];
    let currentResources = [];
    let currentCourses = [];
    let currentFilter = 'all';
    let selectedStudyAction = 'explain';
    let selectedResourceAction = 'summarize';
    let selectedResource = null;
    let activeEditor = null;

    const els = {
        navLinks: document.querySelectorAll('.nav-link'),
        tabContents: document.querySelectorAll('.tab-content'),
        pageTitle: document.getElementById('pageTitle'),
        refreshBtn: document.getElementById('refreshBtn'),
        recentGrid: document.getElementById('recentTasksGrid'),
        allTasksGrid: document.getElementById('allTasksGrid'),
        draftsGrid: document.getElementById('draftsGrid'),
        resourcesGrid: document.getElementById('resourcesGrid'),
        courseResourceFilter: document.getElementById('courseResourceFilter'),
        typeResourceFilter: document.getElementById('typeResourceFilter'),
        resourceStudyWorkbench: document.getElementById('resourceStudyWorkbench'),
        workbenchDocTitle: document.getElementById('workbenchDocTitle'),
        workbenchCourseName: document.getElementById('workbenchCourseName'),
        closeWorkbenchBtn: document.getElementById('closeWorkbenchBtn'),
        resourceToolBtns: document.querySelectorAll('.resource-tool-btn'),
        resourceTopicInput: document.getElementById('resourceTopicInput'),
        runResourceStudyBtn: document.getElementById('runResourceStudyBtn'),
        workbenchResultArea: document.getElementById('workbenchResultArea'),
        workbenchResultHeader: document.getElementById('workbenchResultHeader'),
        workbenchResultText: document.getElementById('workbenchResultText'),
        copyWorkbenchResultBtn: document.getElementById('copyWorkbenchResultBtn'),
        solutionEditorContainer: document.getElementById('solutionEditorContainer'),
        filterBtns: document.querySelectorAll('.filter-btn'),
        pendingOverviewCount: document.getElementById('pendingOverviewCount'),
        draftOverviewCount: document.getElementById('draftOverviewCount'),
        submittedOverviewCount: document.getElementById('submittedOverviewCount'),
        resourcesOverviewCount: document.getElementById('resourcesOverviewCount'),
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

    // Check URL parameters for tab navigation (e.g. ?tab=materials)
    const urlParams = new URLSearchParams(window.location.search);
    const initialTab = urlParams.get('tab') || 'overview';
    switchTab(initialTab);

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
            'materials': 'Course Study Materials & Books',
            'review': 'Review & Edit AI Solutions',
            'study': 'AI Academic Study Tools',
            'history': 'Submission & Task History',
            'settings': 'Settings & LMS Configuration'
        };
        if (els.pageTitle) {
            els.pageTitle.textContent = titles[tabId] || 'Dashboard';
        }

        if (tabId === 'materials') {
            loadResources();
        } else if (tabId === 'history') {
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
    els.refreshBtn.addEventListener('click', async () => {
        StudyMateNotification.info('Scanning Moodle Web Services API for fresh activities...');
        els.refreshBtn.disabled = true;
        try {
            const scanRes = await chrome.runtime.sendMessage({ type: 'TRIGGER_API_SCAN' });
            if (scanRes && scanRes.success) {
                StudyMateNotification.success(scanRes.message || `Refreshed: ${scanRes.totalTasks} tasks, ${scanRes.totalResources} materials.`);
            } else if (scanRes && scanRes.error) {
                StudyMateNotification.warning(scanRes.error);
            }
        } catch (e) {
            console.error('Scan error:', e);
        } finally {
            els.refreshBtn.disabled = false;
            await loadTasks();
            await loadResources();
        }
    });

    // Load Tasks
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

    // Load Learning Resources (Bug 2)
    async function loadResources() {
        try {
            const res = await chrome.runtime.sendMessage({ type: 'GET_RESOURCES' });
            if (res && res.success && Array.isArray(res.resources)) {
                currentResources = res.resources;
                currentCourses = res.courses || [];
            } else if (res && Array.isArray(res.resources)) {
                currentResources = res.resources;
            } else {
                currentResources = [];
            }
            populateCourseFilter();
            renderResourcesGrid();
            if (els.resourcesOverviewCount) {
                els.resourcesOverviewCount.textContent = currentResources.length;
            }
        } catch (e) {
            console.error('Error loading resources:', e);
            StudyMateNotification.error('Failed to load study materials.');
        }
    }

    function populateCourseFilter() {
        if (!els.courseResourceFilter) return;
        const currentVal = els.courseResourceFilter.value;
        els.courseResourceFilter.innerHTML = '<option value="all">All Courses</option>';

        const coursesSeen = new Set();
        currentResources.forEach(r => {
            const cName = r.courseName || r.course || 'Course Resource';
            if (!coursesSeen.has(cName)) {
                coursesSeen.add(cName);
                const opt = document.createElement('option');
                opt.value = cName;
                opt.textContent = cName;
                if (cName === currentVal) opt.selected = true;
                els.courseResourceFilter.appendChild(opt);
            }
        });
    }

    if (els.courseResourceFilter) {
        els.courseResourceFilter.addEventListener('change', renderResourcesGrid);
    }
    if (els.typeResourceFilter) {
        els.typeResourceFilter.addEventListener('change', renderResourcesGrid);
    }

    function renderResourcesGrid() {
        if (!els.resourcesGrid) return;
        els.resourcesGrid.innerHTML = '';

        const courseFilter = els.courseResourceFilter ? els.courseResourceFilter.value : 'all';
        const typeFilter = els.typeResourceFilter ? els.typeResourceFilter.value : 'all';

        let filtered = currentResources;
        if (courseFilter !== 'all') {
            filtered = filtered.filter(r => (r.courseName || r.course) === courseFilter);
        }
        if (typeFilter !== 'all') {
            filtered = filtered.filter(r => (r.resource_type || r.type || 'FILE').toUpperCase() === typeFilter);
        }

        if (filtered.length === 0) {
            const msg = courseFilter !== 'all' ?
                'No study materials were found in this course.' :
                'No study materials discovered yet. Navigate to a Moodle course page and scan.';
            els.resourcesGrid.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">📖</div>
                    <div class="empty-state__title">${msg}</div>
                    <div class="empty-state__desc">PDF books, lecture notes, Word documents, and pages will appear here once discovered.</div>
                </div>`;
            return;
        }

        filtered.forEach(resource => {
            const card = ResourceCard.create(resource, {
                onStudy: (r) => openResourceWorkbench(r),
                onOpen: (r) => console.log('Opening resource:', r.title)
            });
            els.resourcesGrid.appendChild(card);
        });
    }

    // Resource Study Workbench
    function openResourceWorkbench(resource) {
        selectedResource = resource;
        if (!els.resourceStudyWorkbench) return;

        if (els.workbenchDocTitle) els.workbenchDocTitle.textContent = resource.title || resource.file_name || 'Document';
        if (els.workbenchCourseName) els.workbenchCourseName.textContent = resource.courseName || resource.course || 'Course Material';
        if (els.workbenchResultArea) els.workbenchResultArea.style.display = 'none';
        if (els.resourceTopicInput) els.resourceTopicInput.value = '';

        els.resourceStudyWorkbench.style.display = 'block';
        els.resourceStudyWorkbench.scrollIntoView({ behavior: 'smooth' });
    }

    if (els.closeWorkbenchBtn) {
        els.closeWorkbenchBtn.addEventListener('click', () => {
            if (els.resourceStudyWorkbench) els.resourceStudyWorkbench.style.display = 'none';
            selectedResource = null;
        });
    }

    els.resourceToolBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            els.resourceToolBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedResourceAction = btn.getAttribute('data-action');
        });
    });

    if (els.runResourceStudyBtn) {
        els.runResourceStudyBtn.addEventListener('click', async () => {
            if (!selectedResource) {
                StudyMateNotification.warning('Please select a learning resource first.');
                return;
            }

            const topic = els.resourceTopicInput ? els.resourceTopicInput.value.trim() : '';
            const actionLabels = {
                'summarize': 'Summarizing',
                'explain': 'Explaining topic from',
                'notes': 'Generating revision notes for',
                'mcqs': 'Generating MCQs for',
                'practice': 'Generating practice questions for',
                'guide': 'Creating revision guide for'
            };

            StudyMateNotification.info(`${actionLabels[selectedResourceAction] || 'Processing'} "${selectedResource.title}" with AI...`);
            els.runResourceStudyBtn.disabled = true;

            try {
                const res = await chrome.runtime.sendMessage({
                    type: 'STUDY_RESOURCE',
                    payload: {
                        resource_id: selectedResource.id || selectedResource.resource_id,
                        action: selectedResourceAction,
                        topic: topic,
                        text: selectedResource.extracted_text || ''
                    }
                });

                if (res && res.success && res.material) {
                    if (els.workbenchResultArea) els.workbenchResultArea.style.display = 'block';
                    if (els.workbenchResultText) els.workbenchResultText.textContent = res.material;
                    if (els.workbenchResultHeader) {
                        els.workbenchResultHeader.textContent = `${res.action ? res.action.toUpperCase() : 'AI STUDY'} RESULT`;
                    }
                    StudyMateNotification.success(`AI Study material generated successfully!`);
                } else if (res && res.ocr_required) {
                    StudyMateNotification.warning('This document appears to be a scanned image-only PDF. Text extraction requires OCR.');
                } else {
                    StudyMateNotification.error(res?.error || 'Failed to generate study material.');
                }
            } catch (e) {
                console.error('Resource study error:', e);
                StudyMateNotification.error('Error communicating with AI service.');
            } finally {
                els.runResourceStudyBtn.disabled = false;
            }
        });
    }

    if (els.copyWorkbenchResultBtn) {
        els.copyWorkbenchResultBtn.addEventListener('click', () => {
            const text = els.workbenchResultText ? els.workbenchResultText.textContent : '';
            if (text) {
                navigator.clipboard.writeText(text);
                StudyMateNotification.success('Study notes copied to clipboard!');
            }
        });
    }

    // Stats and Grids
    function updateStatsAndGrids() {
        // Pending: Only category 1 (actionable pending)
        const pending = currentTasks.filter(t =>
            (t.is_actionable_pending === 1 || t.isActionablePending === true || t.availability_status === 'AVAILABLE' || t.availabilityStatus === 'AVAILABLE') &&
            t.status !== 'SUBMITTED' && t.status !== 'Submitted' && t.status !== 'COMPLETED' && t.status !== 'Closed' && t.status !== 'Unavailable'
        );
        const drafts = currentTasks.filter(t => t.status === 'GENERATED' || t.status === 'Draft Ready' || t.status === 'REVIEW' || t.status === 'In Draft');
        const submitted = currentTasks.filter(t => t.status === 'SUBMITTED' || t.status === 'Submitted' || t.status === 'COMPLETED');

        if (els.pendingOverviewCount) els.pendingOverviewCount.textContent = pending.length;
        if (els.draftOverviewCount) els.draftOverviewCount.textContent = drafts.length;
        if (els.submittedOverviewCount) els.submittedOverviewCount.textContent = submitted.length;

        renderRecentGrid(pending);
        renderAllTasksGrid();
        renderDraftsGrid();
    }

    function renderRecentGrid(pendingTasks) {
        if (!els.recentGrid) return;
        els.recentGrid.innerHTML = '';
        if (!pendingTasks || pendingTasks.length === 0) {
            els.recentGrid.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">📚</div>
                    <div class="empty-state__title">No pending assignments are currently available in your Moodle courses.</div>
                    <div class="empty-state__desc">Navigate to your Moodle course or assignment page and click "Scan for Assignments" in the popup.</div>
                </div>`;
            return;
        }

        const recent = pendingTasks.slice(0, 4);
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
        if (currentFilter === 'PENDING') {
            filtered = currentTasks.filter(t =>
                (t.is_actionable_pending === 1 || t.isActionablePending === true || t.availability_status === 'AVAILABLE' || t.availabilityStatus === 'AVAILABLE') &&
                t.status !== 'SUBMITTED' && t.status !== 'Submitted' && t.status !== 'COMPLETED'
            );
        } else if (currentFilter !== 'all') {
            filtered = currentTasks.filter(t => (t.type || 'ASSIGNMENT').toUpperCase() === currentFilter.toUpperCase());
        }

        if (filtered.length === 0) {
            const emptyMsg = currentFilter === 'PENDING' ?
                'No pending assignments are currently available in your Moodle courses.' :
                `No ${currentFilter.toLowerCase()} tasks found`;
            els.allTasksGrid.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">🔍</div>
                    <div class="empty-state__title">${emptyMsg}</div>
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
            }
        });
    }

    // Study Tools (General Topic)
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

        if (els.settingsAiProvider && els.settingsAiModel) {
            const currentProvider = els.settingsAiProvider.value;
            els.settingsAiModel.placeholder = PROVIDER_PLACEHOLDERS[currentProvider] || 'e.g. gemini-1.5-flash';
        }

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
    loadResources();
});
