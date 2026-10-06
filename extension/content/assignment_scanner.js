/**
 * StudyMate AI – Moodle Assignment Scanner
 * Extracts title, instructions/description, precise due date, submission status, and grading status.
 */

window.StudyMate = window.StudyMate || {};

window.StudyMate.scanAssignment = () => {
    // 1. Title
    const heading = document.querySelector(".page-header-headings h1, h1, h2.page-header-headings");
    const title = heading ? heading.innerText.trim() : "Untitled Assignment";

    // 2. Instructions / Description
    const descriptionElement = document.querySelector("#intro, #region-main .assignment-content, #region-main .no-overflow, .box.py-3.generalbox");
    let description = descriptionElement ? descriptionElement.innerText.trim() : "";

    // 3. Due Date & Table Metadata
    let dueDate = null;
    let submissionStatus = 'No attempt';
    let gradingStatus = 'Not graded';
    let timeRemaining = null;

    const table = document.querySelector(".submissionstatustable, table.generaltable");
    if (table) {
        const rows = table.querySelectorAll("tr");
        rows.forEach(row => {
            const th = row.querySelector("th, td.c0");
            const td = row.querySelector("td.lastrow, td.c1, td:nth-child(2)");
            if (th && td) {
                const headerText = th.innerText.toLowerCase();
                const valueText = td.innerText.trim();

                if (headerText.includes("due date") || headerText.includes("fälligkeitsdatum")) {
                    dueDate = valueText;
                } else if (headerText.includes("submission status") || headerText.includes("abgabestatus")) {
                    submissionStatus = valueText;
                } else if (headerText.includes("grading status") || headerText.includes("bewertungsstatus")) {
                    gradingStatus = valueText;
                } else if (headerText.includes("time remaining") || headerText.includes("verbleibende zeit")) {
                    timeRemaining = valueText;
                }
            }
        });
    }

    // Direct fallback for simple due date badges
    if (!dueDate) {
        const dueBadge = document.querySelector(".assignment_due_date, [data-region='activity-dates']");
        if (dueBadge) {
            dueDate = dueBadge.innerText.trim();
        }
    }

    return {
        title,
        description,
        dueDate,
        submissionStatus,
        gradingStatus,
        timeRemaining,
        type: "ASSIGNMENT"
    };
};
