const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("file-input");
const loading = document.getElementById("loading");
const errorBox = document.getElementById("error");
const results = document.getElementById("results");
const scoreCircle = document.getElementById("score-circle");
const statsEl = document.getElementById("stats");
const extractedTextEl = document.getElementById("extracted-text");
const suggestionsEl = document.getElementById("suggestions");

dropZone.addEventListener("click", () => fileInput.click());

dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("dragover");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("dragover");
});

dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("dragover");
  if (e.dataTransfer.files.length) {
    handleFile(e.dataTransfer.files[0]);
  }
});

fileInput.addEventListener("change", () => {
  if (fileInput.files.length) {
    handleFile(fileInput.files[0]);
  }
});

async function handleFile(file) {
  reset();
  loading.classList.remove("hidden");

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/analyze", { method: "POST", body: formData });
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || "Something went wrong.");
    }
    renderResults(data);
  } catch (err) {
    showError(err.message);
  } finally {
    loading.classList.add("hidden");
  }
}

function reset() {
  errorBox.classList.add("hidden");
  results.classList.add("hidden");
  suggestionsEl.innerHTML = "";
  statsEl.innerHTML = "";
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
}

function renderResults(data) {
  const { analysis, extracted_text } = data;

  scoreCircle.textContent = analysis.engagement_score;
  extractedTextEl.textContent = extracted_text;

  const stats = analysis.stats;
  const statItems = [
    ["Words", stats.word_count],
    ["Hashtags", stats.hashtag_count],
    ["Mentions", stats.mention_count],
    ["Emojis", stats.emoji_count],
    ["Links", stats.url_count],
    ["Has CTA", stats.has_call_to_action ? "Yes" : "No"],
  ];

  statsEl.innerHTML = statItems
    .map(
      ([label, value]) => `
      <div class="stat">
        <div class="value">${value}</div>
        <div class="label">${label}</div>
      </div>`
    )
    .join("");

  suggestionsEl.innerHTML = analysis.suggestions
    .map(
      (s) => `
      <li class="${s.severity}">
        <span class="category">${s.category}</span>
        ${s.message}
      </li>`
    )
    .join("");

  results.classList.remove("hidden");
}
