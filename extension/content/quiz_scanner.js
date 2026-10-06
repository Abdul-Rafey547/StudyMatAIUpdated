/**
 * StudyMate AI – Moodle Quiz Scanner
 * Extracts quiz title, instructions, time limit, attempts allowed, and structured questions.
 */

window.StudyMate = window.StudyMate || {};

window.StudyMate.scanQuiz = () => {
    // 1. Title
    const heading = document.querySelector(".page-header-headings h1, h1, h2.page-header-headings");
    const title = heading ? heading.innerText.trim() : "Untitled Quiz";

    // 2. Quiz Info & Instructions
    const introElem = document.querySelector("#intro, .quizinfo, .box.py-3.generalbox");
    const description = introElem ? introElem.innerText.trim() : "";

    // 3. Time limit & Attempts
    let timeLimit = null;
    let attempts = null;
    let gradingMethod = null;

    const quizInfoBox = document.querySelector(".quizinfo, .box.generalbox");
    if (quizInfoBox) {
        const text = quizInfoBox.innerText;
        const timeMatch = text.match(/Time limit:\s*([^\n\r]+)/i);
        if (timeMatch) timeLimit = timeMatch[1].trim();

        const attemptsMatch = text.match(/Attempts allowed:\s*([^\n\r]+)/i);
        if (attemptsMatch) attempts = attemptsMatch[1].trim();

        const methodMatch = text.match(/Grading method:\s*([^\n\r]+)/i);
        if (methodMatch) gradingMethod = methodMatch[1].trim();
    }

    // 4. Questions & Answers (during attempt or review)
    const questions = [];
    const questionBlocks = document.querySelectorAll(".que");
    
    questionBlocks.forEach((block, idx) => {
        const textElement = block.querySelector(".qtext");
        const answerElement = block.querySelector(".answer");

        if (textElement) {
            const rawOptions = [];
            if (answerElement) {
                const optionRows = answerElement.querySelectorAll(".r0, .r1, label, div.d-flex");
                if (optionRows.length > 0) {
                    optionRows.forEach(opt => {
                        const optText = opt.innerText.trim();
                        if (optText) rawOptions.push(optText);
                    });
                } else {
                    rawOptions.push(answerElement.innerText.trim());
                }
            }

            questions.push({
                index: idx + 1,
                question: textElement.innerText.trim(),
                options: rawOptions
            });
        }
    });

    return {
        title,
        description,
        timeLimit,
        attempts,
        gradingMethod,
        questions,
        type: "QUIZ"
    };
};
