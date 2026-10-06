console.log("StudyMate AI is running on this Moodle page.");

const currentURL = window.location.href;

// Check what type of Moodle activity this is
let activityType = "UNKNOWN";

if (currentURL.includes("/mod/assign/")) {
  activityType = "ASSIGNMENT";
} else if (currentURL.includes("/mod/quiz/")) {
  activityType = "QUIZ";
}

console.log("Activity type:", activityType);

// Find the main heading (Moodle usually wraps main page headings inside .page-header or h1/h2)
const heading = document.querySelector("h1, h2.page-header-headings");
let activityTitle = heading ? heading.innerText.trim() : "Title Not Found";

console.log("Activity title:", activityTitle);

// Get visible content from Moodle's main region to exclude headers, navbars, and sidebars
const mainContent = document.querySelector("#region-main") || document.body;
const pageText = mainContent.innerText.trim();

console.log("Page text:");
console.log(pageText);