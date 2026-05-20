const chatBox = document.getElementById("chatBox");
const userInput = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");
const languageSelect = document.getElementById("languageSelect");
const requestForm = document.getElementById("requestForm");
const requestStudentName = document.getElementById("requestStudentName");
const requestRollNo = document.getElementById("requestRollNo");
const requestType = document.getElementById("requestType");
const requestPriority = document.getElementById("requestPriority");
const requestReason = document.getElementById("requestReason");
const requestOutput = document.getElementById("requestOutput");
const requestHistory = document.getElementById("requestHistory");
const requestToggle = document.getElementById("requestToggle");
const requestCard = document.getElementById("requestCard");
const requestClose = document.getElementById("requestClose");
const autoOpenedLinks = new Set();
const STATUS_CLASS = {
    "Submitted": "status-submitted",
    "Under Review": "status-review",
    "Approved": "status-approved",
    "Need Admin Action": "status-action",
};

function escapeHtml(text) {
    return String(text || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}

function renderInlineMarkdown(text) {
    return escapeHtml(text)
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.+?)\*/g, "<em>$1</em>");
}

function formatMessage(text) {
    if (!text) return "";

    const normalized = String(text)
        .replace(/\r/g, "")
        .trim();

    const lines = normalized.split("\n");
    const html = [];
    let listItems = [];

    function flushList() {
        if (!listItems.length) return;
        html.push(`<ul>${listItems.join("")}</ul>`);
        listItems = [];
    }

    for (const rawLine of lines) {
        const line = rawLine.trim();

        if (!line) {
            flushList();
            continue;
        }

        if (line.startsWith("### ")) {
            flushList();
            html.push(`<h3>${renderInlineMarkdown(line.slice(4))}</h3>`);
            continue;
        }

        if (line.startsWith("## ")) {
            flushList();
            html.push(`<h2>${renderInlineMarkdown(line.slice(3))}</h2>`);
            continue;
        }

        if (line.startsWith("- ")) {
            listItems.push(`<li>${renderInlineMarkdown(line.slice(2))}</li>`);
            continue;
        }

        if (line.startsWith("\u2022 ")) {
            listItems.push(`<li>${renderInlineMarkdown(line.slice(2))}</li>`);
            continue;
        }

        flushList();
        html.push(`<p>${renderInlineMarkdown(line)}</p>`);
    }

    flushList();
    return html.join("");
}

function tryAutoOpen(meta) {
    if (!meta || !meta.auto_open || !meta.link || autoOpenedLinks.has(meta.link)) {
        return;
    }

    autoOpenedLinks.add(meta.link);
    const opened = window.open(meta.link, "_blank", "noopener,noreferrer");

    if (!opened) {
        console.warn("Popup blocked for auto-open link:", meta.link);
    }
}

function buildResourceCard(meta) {
    if (!meta || !meta.link) return "";

    const label = escapeHtml(
        meta.open_label || (meta.kind === "pdf" ? "Open PDF" : "Open Official Resource")
    );
    const title = meta.title ? `<h4>${escapeHtml(meta.title)}</h4>` : "";

    return `
        <div class="request-meta-card">
            ${title}
            <a href="${escapeHtml(meta.link)}" target="_blank" rel="noopener noreferrer">${label}</a>
        </div>
    `;
}

function renderRequestOutput(message, meta = null, loading = false) {
    if (!requestOutput) return;

    if (loading) {
        requestOutput.innerHTML = `
            <div class="request-response request-loading">
                <h3>Request Assistant</h3>
                <p>Preparing your request support...</p>
            </div>
        `;
        return;
    }

    requestOutput.innerHTML = `
        <div class="request-response">
            <h3>Request Assistant</h3>
            ${formatMessage(message)}
            ${buildResourceCard(meta)}
        </div>
    `;

    tryAutoOpen(meta);
}

function renderRequestHistoryItem(request) {
    if (!requestHistory || !request) return;

    const existing = requestHistory.querySelector(`[data-request-id="${request.request_id}"]`);
    if (existing) {
        existing.remove();
    }

    const item = document.createElement("div");
    item.className = "request-history-item";
    item.dataset.requestId = request.request_id || "";
    const statusClass = STATUS_CLASS[request.status] || "status-submitted";
    const nextLabel = request.status === "Approved" ? "Approved" : (request.status === "Submitted" ? "Move to Review" : "Mark Approved");
    item.innerHTML = `
        <div class="request-history-top">
            <strong>${escapeHtml(request.request_type || "Request")}</strong>
            <span class="request-status-pill ${statusClass}">${escapeHtml(request.status || "Submitted")}</span>
        </div>
        <p><strong>ID:</strong> ${escapeHtml(request.request_id || "Request ID unavailable")}</p>
        <p><strong>Office:</strong> ${escapeHtml(request.office || "Administrative Office")}</p>
        <p><strong>Priority:</strong> ${escapeHtml(request.priority || "Normal")}</p>
        <p class="request-history-time">${escapeHtml(request.created_at || "")}</p>
        <div class="request-history-actions">
            <button type="button" class="request-status-btn" data-request-status="${escapeHtml(request.request_id || "")}" ${request.status === "Approved" ? "disabled" : ""}>
                ${escapeHtml(nextLabel)}
            </button>
        </div>
    `;

    requestHistory.prepend(item);
}

function renderRequestHistory(items) {
    if (!requestHistory) return;

    requestHistory.innerHTML = "";
    if (!items || !items.length) {
        requestHistory.innerHTML = `
            <div class="request-history-empty">
                Your request cards will appear here after submission.
            </div>
        `;
        return;
    }

    items.forEach((item) => renderRequestHistoryItem(item));
}

function setRequestPanel(open) {
    if (!requestCard || !requestToggle) return;

    requestCard.classList.toggle("request-card-collapsed", !open);
    requestToggle.classList.toggle("request-toggle-hidden", open);
    requestToggle.setAttribute("aria-expanded", open ? "true" : "false");
}

async function loadRequestHistory() {
    if (!requestHistory) return;

    try {
        const res = await fetch("/request-support/history");
        const data = await res.json();
        renderRequestHistory(data.requests || []);
    } catch (e) {
        console.error("Request history load error:", e);
    }
}

function addRow(message, who = "bot", meta = null) {
    const row = document.createElement("div");
    row.className = `row ${who === "user" ? "user-row" : "bot-row"}`;

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = who === "user" ? "You" : "AI";

    const contentWrap = document.createElement("div");
    contentWrap.className = "content-wrap";

    const bubble = document.createElement("div");
    bubble.className = `bubble ${who === "user" ? "user" : "bot"}`;
    bubble.innerHTML = formatMessage(message);

    contentWrap.appendChild(bubble);

    if (meta && who === "bot") {
        const card = document.createElement("div");
        card.className = "card";

        if (meta.title) {
            const heading = document.createElement("h4");
            heading.textContent = meta.title;
            card.appendChild(heading);
        }

        if (meta.link) {
            const link = document.createElement("a");
            link.href = meta.link;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            link.className = "resource-link";
            link.textContent = meta.open_label || (meta.kind === "pdf" ? "Open PDF" : "Open Official Resource");
            card.appendChild(link);
        }

        contentWrap.appendChild(card);
        tryAutoOpen(meta);
    }

    row.appendChild(avatar);
    row.appendChild(contentWrap);
    chatBox.appendChild(row);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function addTypingIndicator() {
    const row = document.createElement("div");
    row.className = "row bot-row";
    row.id = "typingRow";

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = "AI";

    const contentWrap = document.createElement("div");
    contentWrap.className = "content-wrap";

    const bubble = document.createElement("div");
    bubble.className = "bubble bot";
    bubble.innerHTML = "<p>Typing...</p>";

    contentWrap.appendChild(bubble);
    row.appendChild(avatar);
    row.appendChild(contentWrap);
    chatBox.appendChild(row);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function removeTypingIndicator() {
    const typingRow = document.getElementById("typingRow");
    if (typingRow) {
        typingRow.remove();
    }
}

async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;

    addRow(message, "user");
    userInput.value = "";
    addTypingIndicator();

    try {
        const res = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message,
                language: languageSelect.value,
            }),
        });

        removeTypingIndicator();

        const data = await res.json();
        addRow(data.reply || "No reply received.", "bot", data.meta || null);
    } catch (e) {
        removeTypingIndicator();
        console.error("Fetch Error:", e);
        addRow(
            "Server se connection nahi ho paa raha hai. Please check whether `py app.py` ya your Flask app running hai.",
            "bot"
        );
    }
}

function sendQuick(text) {
    userInput.value = text;
    sendMessage();
}

async function sendRequestMessage(message) {
    if (!message) return;

    renderRequestOutput("", null, true);

    try {
        const res = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message,
                language: languageSelect.value,
            }),
        });

        const data = await res.json();
        renderRequestOutput(data.reply || "No reply received.", data.meta || null);
    } catch (e) {
        console.error("Request panel fetch error:", e);
        renderRequestOutput(
            "Request section could not connect to the server. Please check whether `py app.py` is running."
        );
    }
}

function sendRequestQuick(text) {
    const payload = {
        student_name: requestStudentName?.value?.trim() || "",
        roll_number: requestRollNo?.value?.trim() || "",
        request_type: text,
        priority: requestPriority?.value?.trim() || "Normal",
        reason: "",
        language: languageSelect.value,
    };
    sendRequestPayload(payload);
}

async function sendRequestPayload(payload) {
    renderRequestOutput("", null, true);

    try {
        const res = await fetch("/request-support", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        const data = await res.json();
        renderRequestOutput(data.reply || "No reply received.", data.meta || null);
        await loadRequestHistory();
    } catch (e) {
        console.error("Request panel fetch error:", e);
        renderRequestOutput(
            "Request section could not connect to the server. Please check whether `py app.py` is running."
        );
    }
}

function submitRequestForm(event) {
    event.preventDefault();

    const studentName = requestStudentName?.value?.trim();
    const rollNumber = requestRollNo?.value?.trim();
    const type = requestType?.value?.trim();
    const priority = requestPriority?.value?.trim();
    const reason = requestReason?.value?.trim();

    if (!type) return;

    sendRequestPayload({
        student_name: studentName,
        roll_number: rollNumber,
        request_type: type,
        priority: priority || "Normal",
        reason,
        language: languageSelect.value,
    });

    if (requestReason) {
        requestReason.value = "";
    }
}

async function updateRequestStatus(requestId) {
    if (!requestId) return;

    renderRequestOutput("", null, true);

    try {
        const res = await fetch("/request-support/status", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ request_id: requestId }),
        });

        const data = await res.json();
        renderRequestOutput(data.reply || "Status updated.", data.meta || null);
        await loadRequestHistory();
    } catch (e) {
        console.error("Request status update error:", e);
        renderRequestOutput("Request status could not be updated right now.");
    }
}

window.sendQuick = sendQuick;
window.sendRequestQuick = sendRequestQuick;

sendBtn.addEventListener("click", sendMessage);
if (requestForm) {
    requestForm.addEventListener("submit", submitRequestForm);
}
userInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
        sendMessage();
    }
});

if (requestHistory) {
    requestHistory.addEventListener("click", (event) => {
        const button = event.target.closest("[data-request-status]");
        if (!button || button.disabled) return;
        updateRequestStatus(button.dataset.requestStatus);
    });
}

if (requestToggle) {
    requestToggle.addEventListener("click", () => setRequestPanel(true));
}

if (requestClose) {
    requestClose.addEventListener("click", () => setRequestPanel(false));
}

loadRequestHistory();
