/**
 * StudyMate AI – Moodle Learning Resource Scanner
 * Scans course pages and resource views for PDFs, books, lecture notes, DOCX, PPTX, TXT, Pages, and learning links.
 * Distinguishes genuine academic materials from UI/navigation elements.
 */

window.StudyMate = window.StudyMate || {};

window.StudyMate.scanResources = () => {
    const resources = [];
    const seenUrls = new Set();
    const courseName = window.StudyMate.detectPage ? window.StudyMate.detectPage().courseName : 'Course Resource';

    // 1. Scan Course Page Activity Elements
    // Moodle uses various containers across versions (4.x: .activity-item, 3.x: .activityinstance, 2.x: li.activity)
    const resourceContainers = document.querySelectorAll(
        '.activity.resource, .activity.folder, .activity.page, .activity.book, .activity.url, ' +
        '.modtype_resource, .modtype_folder, .modtype_page, .modtype_book, .modtype_url, ' +
        '.activity-item[data-activityname], div[data-region="activity-information"]'
    );

    resourceContainers.forEach(container => {
        const link = container.querySelector('a.aalink, a.activityinstance, .activity-item a, a[href*="/mod/"]');
        if (!link || !link.href) return;

        const href = link.href;
        if (seenUrls.has(href)) return;

        // Skip assignments and quizzes (handled by separate scanners)
        if (href.includes('/mod/assign/') || href.includes('/mod/quiz/')) return;

        // Check availability/restrictions
        const isRestricted = container.classList.contains('dimmed') ||
                             container.querySelector('.availabilityinfo, .restrictions') !== null ||
                             container.innerText.toLowerCase().includes('not available unless');

        const titleElem = container.querySelector('.instancename, .activityname, .inplaceeditable, h4') || link;
        let title = titleElem.innerText.trim();
        // Clean out activity tags that Moodle appends (e.g. "File", "URL", "Page", "Book")
        title = title.replace(/\s*(File|URL|Page|Book|Folder|PDF document|Word document|PowerPoint presentation)\s*$/i, '').trim();

        // Detect Resource Type
        let type = 'FILE';
        let fileName = title;
        const lowerHref = href.toLowerCase();
        const containerHtml = container.innerHTML.toLowerCase();

        if (lowerHref.includes('/mod/book/') || container.classList.contains('modtype_book')) {
            type = 'BOOK';
        } else if (lowerHref.includes('/mod/page/') || container.classList.contains('modtype_page')) {
            type = 'PAGE';
        } else if (lowerHref.includes('.pdf') || containerHtml.includes('pdf') || title.toLowerCase().endsWith('.pdf')) {
            type = 'PDF';
            if (!fileName.toLowerCase().endsWith('.pdf')) fileName += '.pdf';
        } else if (lowerHref.includes('.docx') || lowerHref.includes('.doc') || containerHtml.includes('word') || title.toLowerCase().endsWith('.docx')) {
            type = 'DOCX';
            if (!fileName.toLowerCase().endsWith('.docx')) fileName += '.docx';
        } else if (lowerHref.includes('.pptx') || lowerHref.includes('.ppt') || containerHtml.includes('powerpoint')) {
            type = 'PPTX';
            if (!fileName.toLowerCase().endsWith('.pptx')) fileName += '.pptx';
        } else if (lowerHref.includes('.txt') || title.toLowerCase().endsWith('.txt')) {
            type = 'TXT';
            if (!fileName.toLowerCase().endsWith('.txt')) fileName += '.txt';
        } else if (lowerHref.includes('/mod/url/')) {
            type = 'URL';
        }

        // File size if displayed by Moodle
        let fileSize = '';
        const sizeMatch = container.innerText.match(/(\d+(?:\.\d+)?\s*(?:KB|MB|GB|Bytes))/i);
        if (sizeMatch) fileSize = sizeMatch[1];

        // Description / Details if present
        const descElem = container.querySelector('.contentafterlink, .activity-description, .no-overflow');
        const description = descElem ? descElem.innerText.trim() : '';

        // Extract ID
        const matchId = href.match(/id=(\d+)/);
        const resourceId = matchId ? matchId[1] : null;

        seenUrls.add(href);
        resources.push({
            id: resourceId,
            moodle_resource_id: resourceId,
            title: title || 'Learning Resource',
            file_name: fileName,
            resource_type: type,
            type: type,
            file_size: fileSize,
            description: description,
            url: href,
            moodle_url: href,
            course: courseName,
            courseName: courseName,
            availability_status: isRestricted ? 'RESTRICTED' : 'AVAILABLE'
        });
    });

    // 2. Scan Direct File Links (pluginfile.php links that are learning materials)
    const directFileLinks = document.querySelectorAll('a[href*="/pluginfile.php/"]');
    directFileLinks.forEach(link => {
        const href = link.href;
        if (seenUrls.has(href)) return;

        // Skip user avatars, badges, UI assets
        if (href.includes('/user/icon') || href.includes('/badge/') || href.includes('/theme/')) return;

        const text = link.innerText.trim();
        const lowerHref = href.toLowerCase();
        let type = 'FILE';

        if (lowerHref.endsWith('.pdf') || text.toLowerCase().endsWith('.pdf')) type = 'PDF';
        else if (lowerHref.endsWith('.docx') || lowerHref.endsWith('.doc')) type = 'DOCX';
        else if (lowerHref.endsWith('.pptx') || lowerHref.endsWith('.ppt')) type = 'PPTX';
        else if (lowerHref.endsWith('.txt')) type = 'TXT';
        else return; // Only include supported educational documents

        const title = text || href.split('/').pop().replace(/\?.*/, '') || 'Course Document';

        seenUrls.add(href);
        resources.push({
            id: href.match(/\/(\d+)\//)?.[1] || null,
            title: title,
            file_name: title,
            resource_type: type,
            type: type,
            url: href,
            moodle_url: href,
            direct_url: href,
            course: courseName,
            courseName: courseName,
            availability_status: 'AVAILABLE'
        });
    });

    // 3. If currently on a Resource, Page, or Book View page, extract its text content directly
    const currentUrl = window.location.href;
    if (currentUrl.includes('/mod/page/view.php') || currentUrl.includes('/mod/book/view.php') || currentUrl.includes('/mod/resource/view.php')) {
        const heading = document.querySelector('.page-header-headings h1, h1, h2');
        const contentBox = document.querySelector('#region-main .box.py-3.generalbox, .book_content, #region-main .no-overflow, #intro');
        const resText = contentBox ? contentBox.innerText.trim() : '';

        // Check for embedded PDF / resource objects
        const embedObj = document.querySelector('object[data], iframe[src], .resourceworkaround a');
        const directDocUrl = embedObj ? (embedObj.data || embedObj.src || embedObj.href) : null;

        const isBook = currentUrl.includes('/mod/book/');
        const isPage = currentUrl.includes('/mod/page/');
        const type = isBook ? 'BOOK' : (isPage ? 'PAGE' : 'PDF');

        const title = heading ? heading.innerText.trim() : 'Learning Resource';
        const resId = currentUrl.match(/id=(\d+)/)?.[1] || null;

        if (!seenUrls.has(currentUrl)) {
            resources.unshift({
                id: resId,
                moodle_resource_id: resId,
                title: title,
                file_name: `${title}.${type === 'BOOK' || type === 'PAGE' ? 'txt' : 'pdf'}`,
                resource_type: type,
                type: type,
                url: currentUrl,
                moodle_url: currentUrl,
                direct_url: directDocUrl,
                extracted_text: resText,
                course: courseName,
                courseName: courseName,
                availability_status: 'AVAILABLE'
            });
        }
    }

    return resources;
};
