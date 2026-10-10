/**
 * StudyMate AI - Task Card Component
 * Reusable card component for displaying tasks in popup and dashboard.
 */

class TaskCard {
    static create(task, options = {}) {
        const { showActions = true, compact = false, onSolve = null, onView = null } = options;
        
        const typeIcon = task.type === 'QUIZ' ? TaskCard.quizIcon() : TaskCard.assignmentIcon();
        const statusBadge = TaskCard.getStatusBadge(task.status);
        const dueText = TaskCard.formatDueDate(task.dueDate || task.due_date);
        
        const card = document.createElement('div');
        card.className = `task-card ${compact ? 'task-card--compact' : ''}`;
        card.dataset.taskId = task.id || task.task_id || '';
        card.dataset.taskType = task.type || 'ASSIGNMENT';
        
        card.innerHTML = `
            <div class="task-card__header">
                <div class="task-card__icon ${task.type === 'QUIZ' ? 'task-card__icon--quiz' : 'task-card__icon--assignment'}">
                    ${typeIcon}
                </div>
                <div class="task-card__info">
                    <h4 class="task-card__title">${TaskCard.escapeHtml(task.title || 'Untitled Task')}</h4>
                    <p class="task-card__meta">
                        ${TaskCard.escapeHtml(task.course_name || task.courseName || task.course || 'General')}
                        ${dueText ? ` • ${dueText}` : ''}
                    </p>
                </div>
                <span class="task-card__badge ${statusBadge.class}">${statusBadge.label}</span>
            </div>
            ${task.description ? `<p class="task-card__description">${TaskCard.escapeHtml(TaskCard.truncate(task.description, 120))}</p>` : ''}
            ${showActions ? `
            <div class="task-card__actions">
                <button class="task-card__btn task-card__btn--primary solve-btn" data-action="generate" data-task-id="${task.id || task.task_id}">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                    Solve with AI
                </button>
                <button class="task-card__btn task-card__btn--secondary view-btn" data-action="view" data-task-id="${task.id || task.task_id}">
                    View Details
                </button>
                ${(task.moodle_url || task.url) ? `
                <a href="${task.moodle_url || task.url}" target="_blank" class="task-card__btn task-card__btn--secondary moodle-link" style="text-decoration:none; display:inline-flex; align-items:center; gap:4px;" title="Open in Moodle">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                    Moodle
                </a>` : ''}
            </div>` : ''}
        `;
        
        if (showActions) {
            const solveBtn = card.querySelector('.solve-btn');
            const viewBtn = card.querySelector('.view-btn');
            if (solveBtn && onSolve) solveBtn.addEventListener('click', (e) => { e.stopPropagation(); onSolve(task); });
            if (viewBtn && onView) viewBtn.addEventListener('click', (e) => { e.stopPropagation(); onView(task); });
        }
        
        return card;
    }
    
    static getStatusBadge(status) {
        const badges = {
            'DISCOVERED': { label: 'New', class: 'badge--new' },
            'PENDING': { label: 'Pending', class: 'badge--pending' },
            'PROCESSING': { label: 'Processing', class: 'badge--processing' },
            'GENERATED': { label: 'Draft Ready', class: 'badge--draft' },
            'REVIEW': { label: 'In Review', class: 'badge--review' },
            'APPROVED': { label: 'Approved', class: 'badge--approved' },
            'SUBMITTED': { label: 'Submitted', class: 'badge--submitted' },
            'COMPLETED': { label: 'Completed', class: 'badge--completed' },
            'FAILED': { label: 'Failed', class: 'badge--failed' },
            'Draft Ready': { label: 'Draft Ready', class: 'badge--draft' },
            'In Draft': { label: 'In Draft', class: 'badge--draft' },
            'Pending': { label: 'Pending', class: 'badge--pending' }
        };
        return badges[status] || { label: status || 'Pending', class: 'badge--pending' };
    }
    
    static formatDueDate(dateStr) {
        if (!dateStr) return null;
        try {
            const due = new Date(dateStr);
            if (isNaN(due.getTime())) return dateStr;
            const now = new Date();
            const diff = due - now;
            const days = Math.ceil(diff / (1000 * 60 * 60 * 24));
            
            if (days < 0) return 'Overdue';
            if (days === 0) return 'Due today';
            if (days === 1) return 'Due tomorrow';
            if (days <= 7) return `Due in ${days} days`;
            return `Due ${due.toLocaleDateString()}`;
        } catch {
            return dateStr;
        }
    }
    
    static truncate(text, maxLen) {
        if (!text || text.length <= maxLen) return text;
        return text.substring(0, maxLen).trim() + '...';
    }
    
    static escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    static assignmentIcon() {
        return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>`;
    }
    
    static quizIcon() {
        return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;
    }
}

if (typeof window !== 'undefined') {
    window.TaskCard = TaskCard;
}
