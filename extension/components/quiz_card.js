/**
 * StudyMate AI - Quiz Card Component
 * Specialized card for displaying quiz information.
 */

class QuizCard {
    static create(quiz, options = {}) {
        const { onStudy, onPractice } = options;
        const card = document.createElement('div');
        card.className = 'quiz-card';
        card.dataset.quizId = quiz.id || quiz.task_id || '';
        
        const statusBadge = TaskCard ? TaskCard.getStatusBadge(quiz.status) : { label: quiz.status || 'Pending', class: 'badge--pending' };
        
        card.innerHTML = `
            <div class="quiz-card__header">
                <div class="quiz-card__icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
                        <line x1="12" y1="17" x2="12.01" y2="17"/>
                    </svg>
                </div>
                <div class="quiz-card__info">
                    <h4>${QuizCard.escapeHtml(quiz.title || 'Untitled Quiz')}</h4>
                    <p>${quiz.courseName || quiz.course || 'General'}</p>
                </div>
                <span class="task-card__badge ${statusBadge.class}">${statusBadge.label}</span>
            </div>
            ${quiz.questions && quiz.questions.length ? `
            <div class="quiz-card__meta">
                <span>📝 ${quiz.questions.length} question${quiz.questions.length !== 1 ? 's' : ''}</span>
                ${quiz.timeLimit ? `<span>⏱ ${quiz.timeLimit}</span>` : ''}
                ${quiz.attempts ? `<span>🔄 ${quiz.attempts}</span>` : ''}
            </div>` : ''}
            <div class="quiz-card__actions">
                <button class="task-card__btn task-card__btn--secondary study-btn" data-action="study" data-task-id="${quiz.id || quiz.task_id}">
                    📖 Study Mode
                </button>
                <button class="task-card__btn task-card__btn--primary practice-btn" data-action="practice" data-task-id="${quiz.id || quiz.task_id}">
                    🧪 Solve / Practice
                </button>
            </div>
        `;
        
        const studyBtn = card.querySelector('.study-btn');
        const practiceBtn = card.querySelector('.practice-btn');
        if (studyBtn && onStudy) studyBtn.addEventListener('click', (e) => { e.stopPropagation(); onStudy(quiz); });
        if (practiceBtn && onPractice) practiceBtn.addEventListener('click', (e) => { e.stopPropagation(); onPractice(quiz); });
        
        return card;
    }
    
    static escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

if (typeof window !== 'undefined') {
    window.QuizCard = QuizCard;
}
