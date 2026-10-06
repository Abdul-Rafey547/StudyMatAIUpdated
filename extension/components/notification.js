/**
 * StudyMate AI - Notification Component
 * Toast notification system for the extension UI.
 */

class StudyMateNotification {
    static container = null;
    
    static init() {
        if (StudyMateNotification.container && document.body.contains(StudyMateNotification.container)) return;
        StudyMateNotification.container = document.createElement('div');
        StudyMateNotification.container.className = 'sm-notifications';
        StudyMateNotification.container.style.cssText = `
            position: fixed;
            top: 16px;
            right: 16px;
            z-index: 10000;
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-width: 340px;
        `;
        document.body.appendChild(StudyMateNotification.container);
    }
    
    static show(message, type = 'info', duration = 4000) {
        StudyMateNotification.init();
        
        const colors = {
            success: { bg: '#e6f9f3', border: '#00b894', icon: '✓', text: '#1a7a63' },
            error: { bg: '#ffeaea', border: '#ff4757', icon: '✕', text: '#c0392b' },
            warning: { bg: '#fef8e7', border: '#fdcb6e', icon: '⚠', text: '#d68910' },
            info: { bg: '#ede9ff', border: '#6c5ce7', icon: 'ℹ', text: '#5a4bd1' }
        };
        
        const c = colors[type] || colors.info;
        
        const toast = document.createElement('div');
        toast.style.cssText = `
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px 16px;
            background: ${c.bg};
            border: 1px solid ${c.border};
            border-radius: 10px;
            box-shadow: 0 4px 14px rgba(0,0,0,.1);
            font-family: 'Segoe UI', system-ui, sans-serif;
            font-size: 13px;
            color: ${c.text};
            animation: smToastIn 0.3s ease;
            cursor: pointer;
            transition: opacity 0.3s ease;
        `;
        
        toast.innerHTML = `
            <span style="font-size: 16px; flex-shrink: 0;">${c.icon}</span>
            <span style="flex: 1;">${message}</span>
        `;
        
        toast.addEventListener('click', () => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        });
        
        StudyMateNotification.container.appendChild(toast);
        
        if (duration > 0) {
            setTimeout(() => {
                toast.style.opacity = '0';
                setTimeout(() => toast.remove(), 300);
            }, duration);
        }
        
        return toast;
    }
    
    static success(message, duration) { return StudyMateNotification.show(message, 'success', duration); }
    static error(message, duration) { return StudyMateNotification.show(message, 'error', duration); }
    static warning(message, duration) { return StudyMateNotification.show(message, 'warning', duration); }
    static info(message, duration) { return StudyMateNotification.show(message, 'info', duration); }
}

if (typeof window !== 'undefined') {
    window.StudyMateNotification = StudyMateNotification;
    
    if (typeof document !== 'undefined') {
        const style = document.createElement('style');
        style.textContent = `
            @keyframes smToastIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
        `;
        document.head.appendChild(style);
    }
}
