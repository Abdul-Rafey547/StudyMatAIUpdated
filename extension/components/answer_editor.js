/**
 * StudyMate AI - Answer Editor Component
 * Full answer review, editing, and approval interface.
 * Implements the human-in-the-loop review and truthful submission workflow.
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
                        <button class="answer-editor__btn answer-editor__btn--save" id="saveDraftBtn">
                            Save Draft
                        </button>
                        <button class="answer-editor__btn answer-editor__btn--approve" id="approveBtn">
                            ${this.isApproved ? '✓ Approved' : 'Approve Draft'}
                        </button>
                        <button class="answer-editor__btn answer-editor__btn--submit" id="submitBtn" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: #ffffff; font-weight: 600;">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13"/><path d="M22 2L15 22 11 13 2 9l20-7z"/></svg>
                            Submit to Moodle
                        </button>
                    </div>
                </div>
                
                ${this.isApproved ? `
                <div class="answer-editor__submit-section">
                    <div class="answer-editor__approved-badge">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                        Draft approved by student and ready for submission to Moodle
                    </div>
                </div>` : ''}
            </div>
            
            <!-- Submission Confirmation & Format Selection Modal -->
            <div id="submissionModal" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 10000; align-items: center; justify-content: center; backdrop-filter: blur(4px);">
                <div style="background: #ffffff; width: 500px; max-width: 90%; border-radius: 12px; box-shadow: 0 20px 40px rgba(0,0,0,0.3); overflow: hidden; border: 1px solid #e2e8f0; color: #1e293b; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                    <div style="background: #6366f1; color: #ffffff; padding: 16px 20px; font-weight: 600; font-size: 16px; display: flex; justify-content: space-between; align-items: center;">
                        <span>🎓 Moodle Assignment Submission Review</span>
                        <span id="closeModalBtn" style="cursor: pointer; font-size: 20px; line-height: 1;">&times;</span>
                    </div>
                    
                    <div style="padding: 20px;">
                        <div style="margin-bottom: 16px;">
                            <label style="font-size: 11px; text-transform: uppercase; font-weight: 700; color: #64748b; letter-spacing: 0.5px;">Assignment Title</label>
                            <div style="font-weight: 600; font-size: 14px; margin-top: 2px;">${this.escapeHtml(this.task.title || 'Assignment')}</div>
                        </div>

                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px;">
                            <div>
                                <label style="font-size: 11px; text-transform: uppercase; font-weight: 700; color: #64748b; letter-spacing: 0.5px;">Course</label>
                                <div style="font-size: 13px; margin-top: 2px;">${this.escapeHtml(this.task.courseName || this.task.course || 'General Course')}</div>
                            </div>
                            <div>
                                <label style="font-size: 11px; text-transform: uppercase; font-weight: 700; color: #64748b; letter-spacing: 0.5px;">Word Count</label>
                                <div style="font-size: 13px; margin-top: 2px;">${this.countWords(answer)} words (Approved)</div>
                            </div>
                        </div>

                        <div style="margin-bottom: 16px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px;">
                            <label style="font-weight: 600; font-size: 13px; display: block; margin-bottom: 6px;">Select Assignment File Format:</label>
                            <div style="display: flex; gap: 16px;">
                                <label style="display: flex; align-items: center; gap: 6px; font-size: 13px; cursor: pointer;">
                                    <input type="radio" name="modalFileFormat" value="DOCX" checked>
                                    <span><strong>DOCX</strong> (Microsoft Word Document)</span>
                                </label>
                                <label style="display: flex; align-items: center; gap: 6px; font-size: 13px; cursor: pointer;">
                                    <input type="radio" name="modalFileFormat" value="TXT">
                                    <span><strong>TXT</strong> (Plain Text Document)</span>
                                </label>
                            </div>
                        </div>

                        <div style="margin-bottom: 16px;">
                            <button id="modalDownloadBtn" type="button" style="width: 100%; background: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; padding: 10px; border-radius: 8px; font-weight: 600; font-size: 13px; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px;">
                                <span>📥 Download &amp; Inspect File Before Submission</span>
                            </button>
                        </div>

                        <div style="background: #eef2ff; border-left: 4px solid #6366f1; padding: 10px 12px; font-size: 12px; color: #3730a3; margin-bottom: 16px; line-height: 1.4;">
                            ℹ️ <strong>Submission Process:</strong> StudyMate AI will generate your approved file, navigate to Moodle, and prepare the submission. After saving changes, submission status will be verified directly from Moodle.
                        </div>

                        <div id="modalStatusArea" style="display: none; margin-bottom: 16px; padding: 10px; border-radius: 6px; font-size: 12px;"></div>

                        <div style="display: flex; justify-content: flex-end; gap: 10px;">
                            <button id="modalCancelBtn" type="button" style="background: #f1f5f9; border: 1px solid #cbd5e1; color: #475569; padding: 10px 16px; border-radius: 8px; font-weight: 600; font-size: 13px; cursor: pointer;">
                                Cancel
                            </button>
                            <button id="modalProceedBtn" type="button" style="background: #6366f1; border: none; color: #ffffff; padding: 10px 20px; border-radius: 8px; font-weight: 600; font-size: 13px; cursor: pointer; display: flex; align-items: center; gap: 6px;">
                                <span>Proceed to Moodle Submission &rarr;</span>
                            </button>
                        </div>
                    </div>
                </div>
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
        const modal = this.container.querySelector('#submissionModal');
        const closeModalBtn = this.container.querySelector('#closeModalBtn');
        const modalCancelBtn = this.container.querySelector('#modalCancelBtn');
        const modalDownloadBtn = this.container.querySelector('#modalDownloadBtn');
        const modalProceedBtn = this.container.querySelector('#modalProceedBtn');
        const modalStatusArea = this.container.querySelector('#modalStatusArea');

        if (submitBtn && modal) {
            submitBtn.addEventListener('click', () => {
                const editedAnswer = textarea ? textarea.value : '';
                if (!editedAnswer.trim()) {
                    if (window.StudyMateNotification) {
                        window.StudyMateNotification.error('Cannot submit an empty draft. Please generate or enter an answer.');
                    }
                    return;
                }
                if (!this.isApproved) {
                    this.isApproved = true;
                    this.solution.status = 'APPROVED';
                    this.solution.edited_answer = editedAnswer;
                    this.onApprove(this.task, editedAnswer);
                }
                modal.style.display = 'flex';
                if (modalStatusArea) modalStatusArea.style.display = 'none';
            });
        }

        const hideModal = () => {
            if (modal) modal.style.display = 'none';
        };

        if (closeModalBtn) closeModalBtn.addEventListener('click', hideModal);
        if (modalCancelBtn) modalCancelBtn.addEventListener('click', hideModal);

        if (modalDownloadBtn) {
            modalDownloadBtn.addEventListener('click', async () => {
                const formatRadio = this.container.querySelector('input[name="modalFileFormat"]:checked');
                const format = formatRadio ? formatRadio.value : 'DOCX';
                modalDownloadBtn.disabled = true;
                modalDownloadBtn.innerText = 'Generating file...';

                try {
                    const res = await chrome.runtime.sendMessage({
                        type: 'GENERATE_SUBMISSION_FILE',
                        payload: {
                            task_id: this.task.id || this.task.task_id,
                            solution_id: this.solution.solution_id || this.solution.id,
                            format: format,
                            answer: textarea ? textarea.value : ''
                        }
                    });

                    if (res && res.success && res.data_url) {
                        const a = document.createElement('a');
                        a.href = res.data_url;
                        a.download = res.file_name || `Solution.${format.toLowerCase()}`;
                        document.body.appendChild(a);
                        a.click();
                        a.remove();
                        if (window.StudyMateNotification) {
                            window.StudyMateNotification.success(`Downloaded ${res.file_name}`);
                        }
                    } else {
                        if (window.StudyMateNotification) {
                            window.StudyMateNotification.error(res?.error || 'Failed to generate file.');
                        }
                    }
                } catch (e) {
                    console.error('File download error:', e);
                } finally {
                    modalDownloadBtn.disabled = false;
                    modalDownloadBtn.innerHTML = '<span>📥 Download &amp; Inspect File Before Submission</span>';
                }
            });
        }

        if (modalProceedBtn) {
            modalProceedBtn.addEventListener('click', async () => {
                const formatRadio = this.container.querySelector('input[name="modalFileFormat"]:checked');
                const format = formatRadio ? formatRadio.value : 'DOCX';
                
                modalProceedBtn.disabled = true;
                modalProceedBtn.innerHTML = '<span>Preparing Moodle Submission...</span>';
                if (modalStatusArea) {
                    modalStatusArea.style.display = 'block';
                    modalStatusArea.style.background = '#f1f5f9';
                    modalStatusArea.style.color = '#334155';
                    modalStatusArea.innerHTML = '⏳ Generating assignment file and opening Moodle submission interface...';
                }

                try {
                    const res = await chrome.runtime.sendMessage({
                        type: 'PREPARE_SUBMISSION',
                        payload: {
                            task_id: this.task.id || this.task.task_id,
                            solution_id: this.solution.solution_id || this.solution.id,
                            moodle_url: this.task.moodle_url || this.task.url,
                            format: format,
                            answer: textarea ? textarea.value : ''
                        }
                    });

                    if (res && res.success) {
                        const statusMsg = res.submission_status || 'Submitted for grading';
                        const fileName = res.file_name || res.fileName || 'Solution file';
                        
                        if (modalStatusArea) {
                            modalStatusArea.style.display = 'block';
                            modalStatusArea.style.background = '#dcfce7';
                            modalStatusArea.style.color = '#166534';
                            modalStatusArea.innerHTML = `
                                <strong>✅ Assignment Successfully Submitted to Moodle!</strong><br>
                                File: <code>${this.escapeHtml(fileName)}</code><br>
                                Moodle Status: <strong>${this.escapeHtml(statusMsg)}</strong><br>
                                <span style="margin-top: 4px; display: block; font-size: 11px;">Moodle LMS confirmed receipt of your file. Check your Moodle tab to view it!</span>
                            `;
                        }

                        modalProceedBtn.innerHTML = '<span>✅ Submitted to Moodle</span>';
                        modalProceedBtn.disabled = true;
                        if (modalCancelBtn) modalCancelBtn.textContent = 'Close';

                        if (window.StudyMateNotification) {
                            window.StudyMateNotification.success('Assignment successfully uploaded and submitted to Moodle!');
                        }

                        this.solution.status = 'SUBMITTED';
                        this.task.status = 'Submitted';
                        this.task.isActionablePending = false;
                        this.task.availabilityStatus = 'SUBMITTED';
                        this.task.submissionStatus = statusMsg;

                        setTimeout(() => {
                            hideModal();
                            this.render();
                        }, 2500);

                    } else {
                        if (modalStatusArea) {
                            modalStatusArea.style.display = 'block';
                            modalStatusArea.style.background = '#fee2e2';
                            modalStatusArea.style.color = '#991b1b';
                            modalStatusArea.innerHTML = `<strong>Error submitting to Moodle:</strong> ${res?.error || 'Unknown error'}`;
                        }
                        modalProceedBtn.disabled = false;
                        modalProceedBtn.innerHTML = '<span>Retry Submission &rarr;</span>';
                    }
                } catch (e) {
                    console.error('Submission error:', e);
                    modalProceedBtn.disabled = false;
                    modalProceedBtn.innerHTML = '<span>Proceed to Moodle Submission &rarr;</span>';
                }
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
