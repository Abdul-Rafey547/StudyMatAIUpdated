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

            // Inspect Course Activity Links carefully
            const activityItems = document.querySelectorAll('.activity.assign, .activity.quiz, .modtype_assign, .modtype_quiz, .activity-item');
            const discoveredTasks = [];

            activityItems.forEach(item => {
                const link = item.querySelector('a.aalink, a.activityinstance, a[href*="/mod/assign/"], a[href*="/mod/quiz/"]');
                if (!link || !link.href) return;

                const href = link.href;
                const isAssign = href.includes('/mod/assign/');
                const isQuiz = href.includes('/mod/quiz/');
                if (!isAssign && !isQuiz) return;

                const matchId = href.match(/id=(\d+)/);
                const activityId = matchId ? matchId[1] : null;
                const titleElem = item.querySelector('.instancename, .activityname, h4') || link;
                let title = titleElem.innerText.trim();
                title = title.replace(/\s*(Assignment|Quiz)\s*$/i, '').trim();

                // Check completion badges, dates, and restrictions displayed on the course page
                const itemText = item.innerText.toLowerCase();
                const isRestricted = item.classList.contains('dimmed') || itemText.includes('not available unless') || itemText.includes('restricted');
                const isCompleted = item.querySelector('.badge-success, [data-region="completion-info"] .badge-primary, .completion-info .done') !== null || itemText.includes('done:');
                const isSubmitted = itemText.includes('submitted') || itemText.includes('abgegeben');

                // Extract due date if visible in activity summary
                let dueDate = null;
                const dateMatch = item.innerText.match(/Due:\s*([^\n\r]+)/i);
                if (dateMatch) dueDate = dateMatch[1].trim();

                let availStatus = 'UNVERIFIED';
                let isActionable = false;

                if (isRestricted) {
                    availStatus = 'UNAVAILABLE';
                } else if (isCompleted) {
                    availStatus = 'COMPLETED';
                } else if (isSubmitted) {
                    availStatus = 'SUBMITTED';
                } else {
                    // Requires visiting assignment page for verified status — do not assume pending!
                    availStatus = 'UNVERIFIED';
                }

                const taskObj = {
                    id: isAssign ? `assign_${activityId}` : `quiz_${activityId}`,
                    moodle_activity_id: activityId,
                    title: title || (isAssign ? 'Assignment' : 'Quiz'),
                    type: isAssign ? 'ASSIGNMENT' : 'QUIZ',
                    url: href,
                    moodle_url: href,
                    dueDate: dueDate,
                    course: pageInfo.courseName,
                    courseName: pageInfo.courseName,
                    availabilityStatus: availStatus,
                    isActionablePending: isActionable,
                    isUnverified: (availStatus === 'UNVERIFIED'),
                    status: availStatus === 'UNVERIFIED' ? 'Unverified' : (availStatus === 'AVAILABLE' ? 'Pending' : availStatus)
                };

                discoveredTasks.push(taskObj);
                chrome.runtime.sendMessage({
                    type: 'SYNC_SCANNED_TASK',
                    payload: taskObj
                });
            });

            responseData = {
                success: true,
                type: 'COURSE',
                courseName: pageInfo.courseName,
                resourcesFound: resources.length,
                activitiesFound: discoveredTasks.length,
                message: `Discovered ${resources.length} study materials and ${discoveredTasks.length} activities.`
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
