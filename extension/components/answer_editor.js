/**
 * StudyMate AI - Answer Editor Component
 * Full answer review, editing, and approval interface.
 * Implements the human-in-the-loop review workflow.
 */

class AnswerEditor {
    constructor(container, options = {}) {
        this.container = typeof container === 'string' ? document.querySelector(container) : container;
        this.task = options.task || {};
        this.solution = options.solution || {};
        this.onSave = options.onSave || (() => {});
        this.onApprove = options.onApprove || (() => {});
        this.onRegenerate = options.onRegenerate || (() => {});
        this.onSubmit = options.onSubmit || (() => {});
        this.isApproved = (this.solution.status === 'APPROVED');
        this.render();
    }
    
    render() {
        const answer = this.solution.edited_answer || this.solution.generated_answer || '';
        const status = this.solution.status || 'GENERATED';
        this.isApproved = (status === 'APPROVED');
        
        this.container.innerHTML = `
            <div class="answer-editor">
                <div class="answer-editor__header">
                    <div>
                        <h2 class="answer-editor__title">AI Generated Draft</h2>
                        <p class="answer-editor__subtitle">${this.escapeHtml(this.task.title || 'Academic Task')}</p>
                    </div>
                    <span class="answer-editor__status answer-editor__status--${status.toLowerCase()}">${this.getStatusLabel(status)}</span>
                </div>
                
                <div class="answer-editor__meta">
                    <span>📝 ${this.task.type || 'Assignment'}</span>
                    ${this.task.courseName || this.task.course ? `<span>📚 ${this.escapeHtml(this.task.courseName || this.task.course)}</span>` : ''}
                    ${this.solution.created_at ? `<span>🕐 Generated ${new Date(this.solution.created_at).toLocaleString()}</span>` : ''}
                </div>
                
                <div class="answer-editor__content">
                    <label class="answer-editor__label">Student Solution Review &amp; Edit Area</label>
                    <textarea class="answer-editor__textarea" id="answerText" ${this.isApproved ? 'readonly' : ''}
                        placeholder="AI-generated answer will appear here...">${this.escapeHtml(answer)}</textarea>
                    <div class="answer-editor__word-count">
                        <span id="wordCount">${this.countWords(answer)} words</span>
                    </div>
                </div>
                
                <div class="answer-editor__ai-actions">
                    <h3>AI Actions</h3>
                    <div class="answer-editor__btn-group">
                        <button class="answer-editor__btn answer-editor__btn--ai" id="regenerateBtn" ${this.isApproved ? 'disabled' : ''}>
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
                            Regenerate
                        </button>
                        <button class="answer-editor__btn answer-editor__btn--ai" id="improveBtn" ${this.isApproved ? 'disabled' : ''}>
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z"/></svg>
                            Improve &amp; Expand
                        </button>
                        <button class="answer-editor__btn answer-editor__btn--ai" id="explainBtn">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                            Explain Reasoning
                        </button>
                    </div>
                </div>
                
                <div class="answer-editor__divider"></div>
                
                <div class="answer-editor__student-actions">
                    <h3>Student Confirmation &amp; Control</h3>
                    <div class="answer-editor__btn-group">
                        <button class="answer-editor__btn answer-editor__btn--save" id="saveDraftBtn" ${this.isApproved ? 'disabled' : ''}>
                            Save Draft
                        </button>
                        <button class="answer-editor__btn answer-editor__btn--approve" id="approveBtn" ${this.isApproved ? 'disabled' : ''}>
                            ${this.isApproved ? '✓ Approved by Student' : 'Approve Draft'}
                        </button>
                    </div>
                </div>
                
                ${this.isApproved ? `
                <div class="answer-editor__submit-section">
                    <div class="answer-editor__approved-badge">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                        Draft approved by student and ready for submission to Moodle
                    </div>
                    <button class="answer-editor__btn answer-editor__btn--submit" id="submitBtn">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13"/><path d="M22 2L15 22 11 13 2 9l20-7z"/></svg>
                        Submit to Moodle
                    </button>
                </div>` : ''}
            </div>
        `;
        
        this.bindEvents();
    }
    
    bindEvents() {
        const textarea = this.container.querySelector('#answerText');
        const wordCount = this.container.querySelector('#wordCount');
        
        if (textarea && wordCount) {
            textarea.addEventListener('input', () => {
                wordCount.textContent = `${this.countWords(textarea.value)} words`;
            });
        }
        
        const regenerateBtn = this.container.querySelector('#regenerateBtn');
        if (regenerateBtn) {
            regenerateBtn.addEventListener('click', () => this.onRegenerate(this.task));
        }
        
        const improveBtn = this.container.querySelector('#improveBtn');
        if (improveBtn) {
            improveBtn.addEventListener('click', () => {
                const currentText = textarea ? textarea.value : '';
                this.onRegenerate({ ...this.task, custom_prompt: 'Improve and enhance the following answer with more depth, clarity, and precision:\n' + currentText });
            });
        }
        
        const explainBtn = this.container.querySelector('#explainBtn');
        if (explainBtn) {
            explainBtn.addEventListener('click', () => {
                this.onRegenerate({ ...this.task, custom_prompt: 'Explain the reasoning, methodology, and key concepts behind this answer.' });
            });
        }
        
        const saveDraftBtn = this.container.querySelector('#saveDraftBtn');
        if (saveDraftBtn) {
            saveDraftBtn.addEventListener('click', () => {
                const editedAnswer = textarea ? textarea.value : '';
                this.onSave(this.task, editedAnswer);
                if (window.StudyMateNotification) {
                    window.StudyMateNotification.success('Draft saved successfully!');
                }
            });
        }
        
        const approveBtn = this.container.querySelector('#approveBtn');
        if (approveBtn) {
            approveBtn.addEventListener('click', () => {
                const editedAnswer = textarea ? textarea.value : '';
                if (!editedAnswer.trim()) {
                    if (window.StudyMateNotification) {
                        window.StudyMateNotification.error('Cannot approve an empty draft.');
                    }
                    return;
                }
                this.isApproved = true;
                this.solution.status = 'APPROVED';
                this.solution.edited_answer = editedAnswer;
                this.onApprove(this.task, editedAnswer);
                this.render();
                if (window.StudyMateNotification) {
                    window.StudyMateNotification.success('Draft approved! You can now submit to Moodle.');
                }
            });
        }
        
        const submitBtn = this.container.querySelector('#submitBtn');
        if (submitBtn) {
            submitBtn.addEventListener('click', () => {
                this.onSubmit(this.task, this.solution);
            });
        }
    }
    
    getStatusLabel(status) {
        const labels = {
            'GENERATED': '🤖 AI Generated',
            'DRAFT': '📝 Draft',
            'APPROVED': '✅ Approved',
            'SUBMITTED': '📤 Submitted',
            'REVIEW': '👁 In Review'
        };
        return labels[status] || status;
    }
    
    countWords(text) {
        if (!text) return 0;
        return text.trim().split(/\s+/).filter(w => w.length > 0).length;
    }
    
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    getAnswer() {
        const textarea = this.container.querySelector('#answerText');
        return textarea ? textarea.value : '';
    }
}

if (typeof window !== 'undefined') {
    window.AnswerEditor = AnswerEditor;
}
