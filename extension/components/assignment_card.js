/**
 * StudyMate AI - Assignment Card Component
 * Specialized card for displaying assignment information with AI generation capabilities.
 */

class AssignmentCard {
    static create(assignment, options = {}) {
        const { onGenerate, onView } = options;
        const card = document.createElement('div');
        card.className = 'assignment-card';
        card.dataset.taskId = assignment.id || assignment.task_id || '';
        
        const statusBadge = TaskCard ? TaskCard.getStatusBadge(assignment.status) : { label: assignment.status || 'Pending', class: 'badge--pending' };
        const dueText = TaskCard ? TaskCard.formatDueDate(assignment.dueDate || assignment.due_date) : '';
        
        card.innerHTML = `
            <div class="assignment-card__header">
                <div class="assignment-card__icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <polyline points="14 2 14 8 20 8"/>
                        <line x1="16" y1="13" x2="8" y2="13"/>
                        <line x1="16" y1="17" x2="8" y2="17"/>
                    </svg>
                </div>
                <div class="assignment-card__info">
                    <h4>${AssignmentCard.escapeHtml(assignment.title || 'Untitled Assignment')}</h4>
                    <p>${assignment.courseName || assignment.course || 'General'}</p>
                </div>
                <span class="task-card__badge ${statusBadge.class}">${statusBadge.label}</span>
            </div>
            ${dueText ? `<div class="assignment-card__due">📅 ${dueText}</div>` : ''}
            ${assignment.description ? `<p class="assignment-card__desc">${AssignmentCard.escapeHtml(AssignmentCard.truncate(assignment.description, 150))}</p>` : ''}
            <div class="assignment-card__actions">
                <button class="task-card__btn task-card__btn--primary generate-btn" data-action="generate" data-task-id="${assignment.id || assignment.task_id}">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                    Generate Solution
                </button>
                <button class="task-card__btn task-card__btn--secondary view-btn" data-action="view" data-task-id="${assignment.id || assignment.task_id}">
                    View Details
                </button>
            </div>
        `;
        
        const genBtn = card.querySelector('.generate-btn');
        const vBtn = card.querySelector('.view-btn');
        if (genBtn && onGenerate) genBtn.addEventListener('click', (e) => { e.stopPropagation(); onGenerate(assignment); });
        if (vBtn && onView) vBtn.addEventListener('click', (e) => { e.stopPropagation(); onView(assignment); });
        
        return card;
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
}

if (typeof window !== 'undefined') {
    window.AssignmentCard = AssignmentCard;
}
