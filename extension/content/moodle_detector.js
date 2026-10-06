/**
 * StudyMate AI - Moodle Page Detector
 * Identifies if the current page is a Moodle activity or course, and what type it is.
 * Uses both URL pattern matching and DOM inspection for reliable detection.
 */

window.StudyMate = window.StudyMate || {};

window.StudyMate.detectPage = () => {
    const url = window.location.href;
    let type = "NONE";
    let id = null;

    // 1. URL pattern detection
    if (url.includes("/mod/assign/")) {
        type = "ASSIGNMENT";
        const match = url.match(/id=(\d+)/);
        id = match ? match[1] : null;
    } else if (url.includes("/mod/quiz/")) {
        type = "QUIZ";
        const match = url.match(/id=(\d+)/);
        id = match ? match[1] : null;
    } else if (url.includes("/course/view.php")) {
        type = "COURSE";
        const match = url.match(/id=(\d+)/);
        id = match ? match[1] : null;
    }

    // 2. DOM fallback detection if URL is generic
    if (type === "NONE") {
        const bodyClass = document.body ? document.body.className : '';
        if (bodyClass.includes('path-mod-assign')) {
            type = "ASSIGNMENT";
        } else if (bodyClass.includes('path-mod-quiz')) {
            type = "QUIZ";
        } else if (bodyClass.includes('path-course-view')) {
            type = "COURSE";
        } else if (document.querySelector('.path-mod-assign, #page-mod-assign-view')) {
            type = "ASSIGNMENT";
        } else if (document.querySelector('.path-mod-quiz, #page-mod-quiz-view')) {
            type = "QUIZ";
        }
    }

    // Extract Course Name from breadcrumbs or title
    let courseName = 'General';
    const breadcrumb = document.querySelector('.breadcrumb, nav[aria-label="Breadcrumb navigation"]');
    if (breadcrumb) {
        const links = breadcrumb.querySelectorAll('a');
        if (links.length >= 2) {
            courseName = links[links.length - 2].textContent.trim();
        }
    }
    if (courseName === 'General') {
        const pageHeader = document.querySelector('.page-header-headings h1, .breadcrumb-item:nth-last-child(2)');
        if (pageHeader && type !== 'COURSE') {
            courseName = pageHeader.textContent.trim();
        }
    }

    return { type, id, url, courseName };
};

// Immediately notify background script
(async () => {
    try {
        const pageInfo = window.StudyMate.detectPage();
        if (pageInfo.type !== "NONE") {
            await chrome.runtime.sendMessage({ type: 'MOODLE_PAGE_DETECTED', payload: pageInfo });
        }
    } catch (e) {
        // Context invalidated or background starting up
    }
})();
