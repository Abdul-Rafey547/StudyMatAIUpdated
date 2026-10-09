/**
 * StudyMate AI – Moodle Assignment Scanner
 * Accurately extracts title, instructions, due dates, cutoff dates, submission status,
 * grading status, availability indicators, and resubmission permissions.
 * Categorizes assignments strictly into verified availability states.
 */

window.StudyMate = window.StudyMate || {};

window.StudyMate.scanAssignment = () => {
    const url = window.location.href;
    const matchId = url.match(/id=(\d+)/);
    const activityId = matchId ? matchId[1] : null;

    // 1. Title
    const heading = document.querySelector(".page-header-headings h1, h1, h2.page-header-headings, [data-region='header'] h1");
    let title = heading ? heading.innerText.trim() : "Untitled Assignment";
    title = title.replace(/^Assignment\s*[:-]?\s*/i, '').trim();

    // 2. Instructions / Description
    const descriptionElement = document.querySelector("#intro, #region-main .assignment-content, #region-main .no-overflow, .box.py-3.generalbox, .activity-description");
    let description = descriptionElement ? descriptionElement.innerText.trim() : "";

    // 3. Status Table and Notices Metadata
    let dueDate = null;
    let cutoffDate = null;
    let submissionStatus = 'No attempt';
    let gradingStatus = 'Not graded';
    let timeRemaining = null;
    let lastModified = null;
    let hasTable = false;

    const table = document.querySelector(".submissionstatustable, table.generaltable, .submissionsummarytable");
    if (table) {
        hasTable = true;
        const rows = table.querySelectorAll("tr");
        rows.forEach(row => {
            const th = row.querySelector("th, td.c0, td:first-child");
            const td = row.querySelector("td.lastrow, td.c1, td:nth-child(2), td:last-child");
            if (th && td) {
                const headerText = th.innerText.toLowerCase().trim();
                const valueText = td.innerText.trim();

                if (headerText.includes("due date") || headerText.includes("fälligkeitsdatum") || headerText.includes("date limite")) {
                    dueDate = valueText;
                } else if (headerText.includes("cut-off date") || headerText.includes("cutoff date") || headerText.includes("letzter abgabetermin")) {
                    cutoffDate = valueText;
                } else if (headerText.includes("submission status") || headerText.includes("abgabestatus") || headerText.includes("statut des travaux")) {
                    submissionStatus = valueText;
                } else if (headerText.includes("grading status") || headerText.includes("bewertungsstatus") || headerText.includes("statut de l'évaluation")) {
                    gradingStatus = valueText;
                } else if (headerText.includes("time remaining") || headerText.includes("verbleibende zeit") || headerText.includes("temps restant")) {
                    timeRemaining = valueText;
                } else if (headerText.includes("last modified") || headerText.includes("zuletzt geändert") || headerText.includes("dernière modification")) {
                    lastModified = valueText;
                }
            }
        });
    }

    // Direct fallback for due date badges if table lacked it
    if (!dueDate) {
        const dueBadge = document.querySelector(".assignment_due_date, [data-region='activity-dates'], .activity-dates");
        if (dueBadge) {
            const text = dueBadge.innerText;
            const dueMatch = text.match(/Due:\s*([^\n\r]+)/i) || text.match(/Fällig:\s*([^\n\r]+)/i);
            dueDate = dueMatch ? dueMatch[1].trim() : text.trim();
        }
    }

    // 4. Inspect Action Buttons on page
    const addSubBtn = document.querySelector("form input[type='submit'][value*='Add submission' i], form button[type='submit']:contains('Add submission'), a.btn[href*='action=editsubmission'], .singlebutton [value*='Abgabe hinzufügen' i]");
    const editSubBtn = document.querySelector("form input[type='submit'][value*='Edit submission' i], a.btn[href*='action=editsubmission'], [value*='Abgabe bearbeiten' i]");
    const submitAssignmentBtn = document.querySelector("form input[type='submit'][value*='Submit assignment' i], [value*='Abgabe abschließen' i]");

    // 5. Inspect Alerts and Availability Notices
    const notices = Array.from(document.querySelectorAll(".alert, .submissionnotices, .availabilityinfo, .dimmed, [data-region='activity-information']"))
        .map(el => el.innerText.trim().toLowerCase())
        .join(" ");

    const isUpcoming = notices.includes("will accept submissions from") ||
                       notices.includes("nimmt abgaben entgegen ab") ||
                       notices.includes("nicht verfügbar bis");

    const isClosed = notices.includes("submissions are closed") ||
                     notices.includes("not accepting submissions") ||
                     notices.includes("keine abgaben mehr möglich") ||
                     (timeRemaining && (timeRemaining.toLowerCase().includes("assignment is overdue") && !addSubBtn && !editSubBtn));

    const isRestricted = notices.includes("restricted") ||
                         notices.includes("not available unless") ||
                         notices.includes("eingeschränkt") ||
                         document.body.classList.contains("dimmed");

    const subLower = submissionStatus.toLowerCase();
    const gradeLower = gradingStatus.toLowerCase();

    // Check if already submitted
    const isSubmittedForGrading = subLower.includes("submitted for grading") ||
                                  subLower.includes("abgegeben zur bewertung") ||
                                  subLower.includes("rendu pour évaluation");

    const isDraftNotSubmitted = subLower.includes("draft (not submitted)") ||
                                subLower.includes("entwurf") ||
                                subLower.includes("brouillon");

    const isGraded = gradeLower.includes("graded") || gradeLower.includes("bewertet");

    // Check resubmission permissions
    const resubmissionAllowed = Boolean(editSubBtn || (isSubmittedForGrading && subLower.includes("reopened")));

    // 6. Strict Availability Categorization
    let availabilityStatus = 'AVAILABLE';
    let isActionablePending = false;
    let status = 'Pending';

    if (isRestricted) {
        availabilityStatus = 'UNAVAILABLE';
        isActionablePending = false;
        status = 'Unavailable';
    } else if (isUpcoming) {
        availabilityStatus = 'UPCOMING';
        isActionablePending = false;
        status = 'Upcoming';
    } else if (isClosed && !resubmissionAllowed) {
        availabilityStatus = 'CLOSED';
        isActionablePending = false;
        status = 'Closed';
    } else if (isGraded && !resubmissionAllowed) {
        availabilityStatus = 'COMPLETED';
        isActionablePending = false;
        status = 'Completed';
    } else if (isSubmittedForGrading && !resubmissionAllowed) {
        availabilityStatus = 'SUBMITTED';
        isActionablePending = false;
        status = 'Submitted';
    } else if (!hasTable && !addSubBtn && !editSubBtn && !description) {
        // Cannot determine status reliably — never assume pending!
        availabilityStatus = 'UNVERIFIED';
        isActionablePending = false;
        status = 'Unverified';
    } else {
        // Open for student action
        availabilityStatus = 'AVAILABLE';
        isActionablePending = true;
        if (isDraftNotSubmitted) {
            status = 'Draft Ready';
        } else if (resubmissionAllowed) {
            status = 'Pending (Resubmission Allowed)';
        } else {
            status = 'Pending';
        }
    }

    return {
        id: activityId,
        moodle_activity_id: activityId,
        title,
        description,
        dueDate,
        cutoffDate,
        submissionStatus,
        gradingStatus,
        timeRemaining,
        lastModified,
        availabilityStatus,
        isActionablePending,
        resubmissionAllowed,
        status,
        url,
        type: "ASSIGNMENT"
    };
};
