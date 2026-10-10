/**
 * StudyMate AI – Moodle Submission Helper & Verification Script
 * Manages file attachment to Moodle submission forms, handles submission actions,
 * and verifies actual Moodle submission status truthfully.
 */

window.StudyMate = window.StudyMate || {};

window.StudyMate.submissionHelper = {
    /**
     * Inspect current page to verify Moodle's actual resulting submission status.
     */
    verifySubmissionState: () => {
        const table = document.querySelector(".submissionstatustable, table.generaltable, .submissionsummarytable");
        let submissionStatus = 'Unknown';
        let gradingStatus = 'Not graded';
        let lastModified = null;
        let submissionFiles = [];

        if (table) {
            const rows = table.querySelectorAll("tr");
            rows.forEach(row => {
                const th = row.querySelector("th, td.c0, td:first-child");
                const td = row.querySelector("td.lastrow, td.c1, td:nth-child(2), td:last-child");
                if (th && td) {
                    const h = th.innerText.toLowerCase().trim();
                    const v = td.innerText.trim();
                    if (h.includes("submission status") || h.includes("abgabestatus")) {
                        submissionStatus = v;
                    } else if (h.includes("grading status") || h.includes("bewertungsstatus")) {
                        gradingStatus = v;
                    } else if (h.includes("last modified") || h.includes("zuletzt geändert")) {
                        lastModified = v;
                    } else if (h.includes("file submissions") || h.includes("dateiabgabe")) {
                        submissionFiles = Array.from(td.querySelectorAll("a")).map(a => a.innerText.trim()).filter(Boolean);
                    }
                }
            });
        }

        const subLower = submissionStatus.toLowerCase();
        const isSubmitted = subLower.includes("submitted for grading") ||
                            subLower.includes("abgegeben zur bewertung") ||
                            subLower.includes("rendu pour évaluation");

        const isDraft = subLower.includes("draft (not submitted)") ||
                        subLower.includes("entwurf") ||
                        subLower.includes("brouillon");

        // Check for Moodle error notices
        const errorAlert = document.querySelector(".alert-danger, .notifyproblem, .errormessage, .fitem.has-danger");
        const errorText = errorAlert ? errorAlert.innerText.trim() : null;

        return {
            verified: isSubmitted,
            isDraft: isDraft,
            submissionStatus,
            gradingStatus,
            lastModified,
            submissionFiles,
            errorText,
            url: window.location.href
        };
    },

    /**
     * Attach a generated file (DOCX or TXT) and online text to Moodle's submission form.
     */
    prepareSubmissionForm: async (payload) => {
        const solution = payload.solution || payload || {};
        const answerText = solution.edited_answer || solution.generated_answer || '';
        const fileBase64 = payload.file_base64;
        const fileName = payload.file_name || 'Assignment_Solution.docx';
        const mimeType = payload.mime_type || 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';

        let filledText = false;
        let fileAttached = false;
        let errors = [];

        // 1. Fill Online Text if supported on this form
        const textarea = document.querySelector("#id_onlinetext_editor, textarea.form-control, #id_submissioncomment, textarea[name='onlinetext_editor[text]']");
        if (textarea) {
            textarea.value = answerText;
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
            textarea.dispatchEvent(new Event('change', { bubbles: true }));
            filledText = true;
        }

        const attoEditable = document.querySelector("#id_onlinetext_editoreditable, .editor_atto_content, div[contenteditable='true']");
        if (attoEditable) {
            attoEditable.innerHTML = answerText.replace(/\n/g, '<br>');
            attoEditable.dispatchEvent(new Event('input', { bubbles: true }));
            attoEditable.dispatchEvent(new Event('change', { bubbles: true }));
            filledText = true;
        }

        const iframe = document.querySelector("#id_onlinetext_editor_ifr, iframe.tox-edit-area__iframe");
        if (iframe && iframe.contentDocument && iframe.contentDocument.body) {
            iframe.contentDocument.body.innerHTML = answerText.replace(/\n/g, '<br>');
            iframe.contentDocument.dispatchEvent(new Event('input', { bubbles: true }));
            filledText = true;
        }

        // 2. Attach File into Moodle Filemanager if fileBase64 provided
        if (fileBase64) {
            try {
                // Convert base64 to File object
                const byteCharacters = atob(fileBase64);
                const byteNumbers = new Array(byteCharacters.length);
                for (let i = 0; i < byteCharacters.length; i++) {
                    byteNumbers[i] = byteCharacters.charCodeAt(i);
                }
                const byteArray = new Uint8Array(byteNumbers);
                const blob = new Blob([byteArray], { type: mimeType });
                const file = new File([blob], fileName, { type: mimeType, lastModified: Date.now() });

                // Try Standard File Input if present
                const fileInput = document.querySelector("input[type='file'], input[name='files_filemanager'], .fp-file input[type='file']");
                if (fileInput) {
                    try {
                        const dataTransfer = new DataTransfer();
                        dataTransfer.items.add(file);
                        fileInput.files = dataTransfer.files;
                        fileInput.dispatchEvent(new Event('change', { bubbles: true }));
                        fileAttached = true;
                    } catch (e) {
                        console.warn('[StudyMate AI] File input assignment fallback:', e);
                    }
                }

                // Try Moodle Dropzone Target
                const dropzone = document.querySelector(".dndupload-target, .filemanager, .fm-empty-container");
                if (dropzone) {
                    try {
                        const dataTransfer = new DataTransfer();
                        dataTransfer.items.add(file);
                        const dropEvent = new DragEvent('drop', {
                            bubbles: true,
                            cancelable: true,
                            dataTransfer: dataTransfer
                        });
                        dropzone.dispatchEvent(dropEvent);
                        fileAttached = true;
                    } catch (e) {
                        console.warn('[StudyMate AI] Dropzone simulation fallback:', e);
                    }
                }

                // Show floating helper overlay to guide the student directly on the Moodle page
                const downloadUrl = payload.data_url || (fileBase64 ? `data:${mimeType};base64,${fileBase64}` : '');
                window.StudyMate.submissionHelper.renderFloatingHelper(file, fileName, downloadUrl, answerText);

            } catch (e) {
                console.error('[StudyMate AI] Error attaching file:', e);
                errors.push(e.message);
            }
        }

        return {
            success: filledText || fileAttached || Boolean(fileBase64),
            filledText,
            fileAttached,
            fileName,
            errors
        };
    },

    /**
     * Render a floating StudyMate submission assistant on Moodle assignment pages.
     */
    renderFloatingHelper: (fileObj, fileName, downloadUrl, answerText) => {
        let existing = document.getElementById('studymate-submission-helper');
        if (existing) existing.remove();

        const helper = document.createElement('div');
        helper.id = 'studymate-submission-helper';
        helper.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 24px;
            width: 340px;
            background: #ffffff;
            color: #1e293b;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.25);
            border: 2px solid #6366f1;
            z-index: 999999;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            font-size: 13px;
            overflow: hidden;
        `;

        helper.innerHTML = `
            <div style="background: #6366f1; color: #ffffff; padding: 10px 14px; font-weight: 600; display: flex; justify-content: space-between; align-items: center;">
                <span>🎓 StudyMate AI Submission Helper</span>
                <span id="studymate-helper-close" style="cursor: pointer; font-size: 16px;">×</span>
            </div>
            <div style="padding: 14px;">
                <p style="margin: 0 0 8px 0; font-weight: 600;">Generated File Ready:</p>
                <div style="background: #f1f5f9; padding: 8px 10px; border-radius: 6px; font-family: monospace; font-size: 12px; margin-bottom: 12px; word-break: break-all;">
                    📄 ${fileName}
                </div>
                <div style="display: flex; gap: 8px; margin-bottom: 12px;">
                    <a href="${downloadUrl}" download="${fileName}" style="flex: 1; text-align: center; background: #0ea5e9; color: #fff; padding: 8px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 12px;">
                        📥 Download File
                    </a>
                </div>
                <div style="font-size: 11px; color: #64748b; line-height: 1.4; border-top: 1px solid #e2e8f0; padding-top: 10px;">
                    <strong>Next Steps:</strong><br>
                    1. Upload or drag your file into the Moodle file box above.<br>
                    2. Click <strong>"Save changes"</strong>.<br>
                    3. If required, click <strong>"Submit assignment"</strong> to finalize.
                </div>
            </div>
        `;

        document.body.appendChild(helper);

        const closeBtn = document.getElementById('studymate-helper-close');
        if (closeBtn) closeBtn.addEventListener('click', () => helper.remove());
    }
};
