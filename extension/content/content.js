/**
 * StudyMate AI – Content Script Orchestrator
 * Coordinates page detection, assignment scanning, resource discovery,
 * file submission injection, and truthful Moodle submission verification.
 */

console.log("[StudyMate AI] Initialized on:", window.location.href);

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    const action = message.type || message.action;

    if (action === 'SCAN_PAGE_NOW') {
        const pageInfo = window.StudyMate.detectPage ? window.StudyMate.detectPage() : { type: 'NONE' };
        let responseData = { success: false };

        if (pageInfo.type === 'ASSIGNMENT') {
            const assignment = window.StudyMate.scanAssignment();
            const taskId = assignment.id || pageInfo.id || 'assign_' + Date.now();

            chrome.runtime.sendMessage({
                type: 'SYNC_SCANNED_TASK',
                payload: {
                    ...assignment,
                    course: pageInfo.courseName,
                    courseName: pageInfo.courseName,
                    id: taskId,
                    task_id: taskId,
                    url: pageInfo.url
                }
            });

            responseData = {
                success: true,
                type: 'ASSIGNMENT',
                title: assignment.title,
                status: assignment.status,
                availabilityStatus: assignment.availabilityStatus,
                isActionablePending: assignment.isActionablePending,
                data: assignment
            };

        } else if (pageInfo.type === 'QUIZ') {
            const quiz = window.StudyMate.scanQuiz ? window.StudyMate.scanQuiz() : {};
            const taskId = pageInfo.id ? `quiz_${pageInfo.id}` : 'quiz_' + Date.now();

            chrome.runtime.sendMessage({
                type: 'SYNC_SCANNED_TASK',
                payload: {
                    ...quiz,
                    course: pageInfo.courseName,
                    courseName: pageInfo.courseName,
                    id: taskId,
                    task_id: taskId,
                    url: pageInfo.url
                }
            });

            responseData = {
                success: true,
                type: 'QUIZ',
                title: quiz.title,
                data: quiz
            };

        } else if (pageInfo.type === 'RESOURCE' || pageInfo.type === 'PAGE' || pageInfo.type === 'BOOK' || pageInfo.type === 'FOLDER') {
            // Dedicated Resource Scanner
            const resources = window.StudyMate.scanResources ? window.StudyMate.scanResources() : [];
            if (resources.length > 0) {
                chrome.runtime.sendMessage({
                    type: 'SYNC_SCANNED_RESOURCES',
                    payload: {
                        resources: resources,
                        course: pageInfo.courseName
                    }
                });
            }
            responseData = {
                success: true,
                type: pageInfo.type,
                resourceCount: resources.length,
                resources: resources
            };

        } else if (pageInfo.type === 'COURSE') {
            // Course page: Scan both learning resources AND course activity links with availability inspection
            const resources = window.StudyMate.scanResources ? window.StudyMate.scanResources() : [];
            if (resources.length > 0) {
                chrome.runtime.sendMessage({
                    type: 'SYNC_SCANNED_RESOURCES',
                    payload: {
                        resources: resources,
                        course: pageInfo.courseName
                    }
                });
            }

            // On course pages, study materials (PDFs, notes, pages, books) are discovered.
            // Authentic course tasks and availability are governed strictly by the Moodle Web Services API.
            responseData = {
                success: true,
                type: 'COURSE',
                courseName: pageInfo.courseName,
                resourcesFound: resources.length,
                message: `Discovered ${resources.length} study materials in course "${pageInfo.courseName}".`
            };
        } else {
            responseData = {
                success: false,
                error: 'Current page is not recognized as a Moodle course, assignment, or resource.'
            };
        }

        sendResponse(responseData);
        return true;

    } else if (action === 'FILL_MOODLE_SUBMISSION' || action === 'PREPARE_MOODLE_SUBMISSION') {
        if (window.StudyMate && window.StudyMate.submissionHelper) {
            window.StudyMate.submissionHelper.prepareSubmissionForm(message.payload).then(res => {
                sendResponse(res);
            }).catch(err => {
                sendResponse({ success: false, error: err.message });
            });
            return true;
        } else {
            sendResponse({ success: false, error: 'Submission helper not loaded.' });
        }

    } else if (action === 'VERIFY_MOODLE_SUBMISSION') {
        if (window.StudyMate && window.StudyMate.submissionHelper) {
            const verification = window.StudyMate.submissionHelper.verifySubmissionState();
            sendResponse({ success: true, verification });
        } else {
            sendResponse({ success: false, error: 'Submission helper not loaded.' });
        }
        return true;
    }

    return true;
});
