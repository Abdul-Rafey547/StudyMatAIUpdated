/**
 * StudyMate AI - Resource Card Component
 * Specialized card for displaying Moodle learning materials (PDF books, notes, DOCX, Pages, Books)
 * with direct link opening and AI study tools.
 */

class ResourceCard {
    static create(resource, options = {}) {
        const { onStudy, onOpen } = options;
        const card = document.createElement('div');
        card.className = 'resource-card task-card';
        card.dataset.resourceId = resource.id || resource.resource_id || '';
        
        const type = (resource.resource_type || resource.type || 'PDF').toUpperCase();
        const icon = ResourceCard.getTypeIcon(type);
        const typeBadge = ResourceCard.getTypeBadge(type);
        
        const moodleUrl = resource.url || resource.moodle_url || resource.direct_url || '#';
        const title = resource.title || resource.file_name || 'Learning Material';
        const courseName = resource.courseName || resource.course || 'Course Resource';
        const description = resource.description || '';
        const fileSize = resource.file_size || resource.fileSize || '';

        card.innerHTML = `
            <div class="task-card__header">
                <div class="task-card__icon task-card__icon--resource" style="background: rgba(99, 102, 241, 0.1); color: #6366f1; display: flex; align-items: center; justify-content: center; width: 36px; height: 36px; border-radius: 8px;">
                    ${icon}
                </div>
                <div class="task-card__info" style="flex: 1; min-width: 0;">
                    <h4 class="task-card__title" title="${ResourceCard.escapeHtml(title)}" style="font-size: 14px; font-weight: 600; margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                        ${ResourceCard.escapeHtml(title)}
                    </h4>
                    <p class="task-card__meta" style="font-size: 12px; color: var(--text-secondary, #64748b); margin: 2px 0 0 0;">
                        ${ResourceCard.escapeHtml(courseName)}${fileSize ? ` • ${fileSize}` : ''}
                    </p>
                </div>
                <span class="task-card__badge ${typeBadge.class}">${typeBadge.label}</span>
            </div>
            ${description ? `<p class="task-card__description" style="font-size: 12px; color: var(--text-secondary, #475569); margin: 10px 0 12px 0;">${ResourceCard.escapeHtml(ResourceCard.truncate(description, 140))}</p>` : ''}
            <div class="task-card__actions" style="display: flex; gap: 8px; margin-top: 12px;">
                <a href="${moodleUrl}" target="_blank" rel="noopener noreferrer" class="task-card__btn task-card__btn--secondary open-resource-btn" style="text-decoration: none; display: flex; align-items: center; gap: 6px; padding: 6px 12px; font-size: 12px; border-radius: 6px; border: 1px solid var(--border-color, #cbd5e1); color: var(--text-primary, #334155);">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                    Open Resource
                </a>
                <button class="task-card__btn task-card__btn--primary study-resource-btn" data-action="study" style="display: flex; align-items: center; gap: 6px; padding: 6px 14px; font-size: 12px; border-radius: 6px; background: #6366f1; color: #ffffff; border: none; font-weight: 600; cursor: pointer;">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                    Study with AI
                </button>
            </div>
        `;
        
        const studyBtn = card.querySelector('.study-resource-btn');
        const openBtn = card.querySelector('.open-resource-btn');
        if (studyBtn && onStudy) studyBtn.addEventListener('click', (e) => { e.stopPropagation(); onStudy(resource); });
        if (openBtn && onOpen) openBtn.addEventListener('click', (e) => { onOpen(resource); });
        
        return card;
    }
    
    static getTypeBadge(type) {
        const badges = {
            'PDF': { label: 'PDF Book / Doc', class: 'badge--pdf' },
            'DOCX': { label: 'Word Document', class: 'badge--doc' },
            'PPTX': { label: 'Presentation', class: 'badge--ppt' },
            'TXT': { label: 'Text Notes', class: 'badge--txt' },
            'BOOK': { label: 'Moodle Book', class: 'badge--book' },
            'PAGE': { label: 'Moodle Page', class: 'badge--page' },
            'URL': { label: 'Web Resource', class: 'badge--url' },
            'FILE': { label: 'Course File', class: 'badge--file' }
        };
        return badges[type] || { label: type, class: 'badge--file' };
    }
    
    static getTypeIcon(type) {
        if (type === 'PDF') {
            return `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/></svg>`;
        }
        if (type === 'BOOK' || type === 'PAGE') {
            return `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>`;
        }
        return `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg>`;
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
    window.ResourceCard = ResourceCard;
}
