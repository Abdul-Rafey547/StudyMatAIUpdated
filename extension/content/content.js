/**
 * StudyMate AI – Content Script Orchestrator
 * Listens for commands from the popup/dashboard and communicates with background service worker.
 */

console.log("[StudyMate AI] Initialized on:", window.location.href);

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'SCAN_PAGE_NOW') {
        const pageInfo = window.StudyMate.detectPage();
        let result = null;

        if (pageInfo.type === 'ASSIGNMENT') {
            result = window.StudyMate.scanAssignment();
        } else if (pageInfo.type === 'QUIZ') {
            result = window.StudyMate.scanQuiz();
        } else if (pageInfo.type === 'COURSE') {
            // Scan course page for activity links
            const activityLinks = document.querySelectorAll('.activityinstance a, .activity-item a, a.aalink');
            const detectedActivities = [];
            activityLinks.forEach(link => {
                const href = link.href;
                const text = link.innerText.trim();
                if (href.includes('/mod/assign/')) {
                    detectedActivities.push({ title: text, type: 'ASSIGNMENT', url: href });
                } else if (href.includes('/mod/quiz/')) {
                    detectedActivities.push({ title: text, type: 'QUIZ', url: href });
                }
            });

            if (detectedActivities.length > 0) {
                // Sync discovered activities
                detectedActivities.forEach(act => {
                    chrome.runtime.sendMessage({
                        type: 'SYNC_SCANNED_TASK',
                        payload: {
                            ...act,
                            course: pageInfo.courseName,
                            id: act.url.match(/id=(\d+)/)?.[1] || Date.now().toString()
                        }
                    });
                });
                sendResponse({ success: true, message: `Discovered ${detectedActivities.length} activities on course page.` });
                return true;
            }
        }

        if (result) {
            // Forward scanned data to background to save
            chrome.runtime.sendMessage({
                type: 'SYNC_SCANNED_TASK',
                payload: {
                    ...result,
                    course: pageInfo.courseName,
                    courseName: pageInfo.courseName,
                    id: pageInfo.id || Date.now().toString(),
                    url: pageInfo.url
                }
            });
            sendResponse({ success: true, data: result });
        } else {
            sendResponse({ success: false, error: 'Not an assignment, quiz, or course activity page.' });
        }
    } else if (message.type === 'FILL_MOODLE_SUBMISSION') {
        const solution = message.payload?.solution || message.payload || {};
        const answerText = solution.edited_answer || solution.generated_answer || '';
        console.log("[StudyMate AI] Filling Moodle submission with text:", answerText.substring(0, 50) + '...');

        let filled = false;

        // 1. Standard Textareas
        const textarea = document.querySelector("#id_onlinetext_editor, textarea.form-control, #id_submissioncomment, textarea[name='onlinetext_editor[text]']");
        if (textarea) {
            textarea.value = answerText;
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
            textarea.dispatchEvent(new Event('change', { bubbles: true }));
            filled = true;
        }

        // 2. Moodle Atto / Contenteditable Editor
        const attoEditable = document.querySelector("#id_onlinetext_editoreditable, .editor_atto_content, div[contenteditable='true']");
        if (attoEditable) {
            attoEditable.innerHTML = answerText.replace(/\n/g, '<br>');
            attoEditable.dispatchEvent(new Event('input', { bubbles: true }));
            attoEditable.dispatchEvent(new Event('change', { bubbles: true }));
            filled = true;
        }

        // 3. TinyMCE Iframe Editor
        const iframe = document.querySelector("#id_onlinetext_editor_ifr, iframe.tox-edit-area__iframe");
        if (iframe && iframe.contentDocument) {
            const iframeBody = iframe.contentDocument.body;
            if (iframeBody) {
                iframeBody.innerHTML = answerText.replace(/\n/g, '<br>');
                iframe.contentDocument.dispatchEvent(new Event('input', { bubbles: true }));
                filled = true;
            }
        }

        if (filled) {
            sendResponse({ success: true, message: 'Solution inserted into Moodle submission editor.' });
        } else {
            sendResponse({ success: false, message: 'Could not find a recognized submission editor on this page.' });
        }
    }
    return true;
});
