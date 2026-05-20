const adminRequestList = document.getElementById("adminRequestList");
const adminMessage = document.getElementById("adminMessage");
const statTotal = document.getElementById("statTotal");
const statSubmitted = document.getElementById("statSubmitted");
const statReview = document.getElementById("statReview");
const statApproved = document.getElementById("statApproved");

function esc(text) {
    return String(text || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}

function setStats(stats = {}) {
    statTotal.textContent = stats.total ?? 0;
    statSubmitted.textContent = stats.submitted ?? 0;
    statReview.textContent = stats.under_review ?? 0;
    statApproved.textContent = stats.approved ?? 0;
}

function renderRequests(requests = []) {
    if (!adminRequestList) return;

    if (!requests.length) {
        adminRequestList.innerHTML = `<div class="admin-empty">No requests submitted yet.</div>`;
        return;
    }

    adminRequestList.innerHTML = requests.map((request) => `
        <article class="admin-request-card" data-request-id="${esc(request.request_id)}">
            <div class="admin-request-head">
                <div>
                    <h3>${esc(request.request_type)}</h3>
                    <p>${esc(request.request_id)} - ${esc(request.office || "Administrative Office")}</p>
                </div>
                <span class="admin-status">${esc(request.status)}</span>
            </div>

            <div class="admin-request-grid">
                <p><strong>Student:</strong> ${esc(request.student_name || "Not provided")}</p>
                <p><strong>Roll No:</strong> ${esc(request.roll_number || "Not provided")}</p>
                <p><strong>Priority:</strong> ${esc(request.priority || "Normal")}</p>
                <p><strong>Created:</strong> ${esc(request.created_at || "-")}</p>
            </div>

            <div class="admin-reason">
                <strong>Reason</strong>
                <p>${esc(request.reason || "No reason shared by the student.")}</p>
            </div>

            <div class="admin-actions">
                <label>
                    Status
                    <select class="admin-status-select">
                        <option value="Submitted" ${request.status === "Submitted" ? "selected" : ""}>Submitted</option>
                        <option value="Under Review" ${request.status === "Under Review" ? "selected" : ""}>Under Review</option>
                        <option value="Approved" ${request.status === "Approved" ? "selected" : ""}>Approved</option>
                        <option value="Need Admin Action" ${request.status === "Need Admin Action" ? "selected" : ""}>Need Admin Action</option>
                    </select>
                </label>

                <label>
                    Admin Note
                    <textarea class="admin-note-input" rows="3" placeholder="Add internal admin note...">${esc(request.admin_note || "")}</textarea>
                </label>

                <button type="button" class="admin-update-btn">Update Request</button>
            </div>
        </article>
    `).join("");
}

async function loadAdminRequests() {
    try {
        const res = await fetch("/admin/requests");
        const data = await res.json();
        setStats(data.stats || {});
        renderRequests(data.requests || []);
    } catch (error) {
        console.error("Admin request load error:", error);
        adminMessage.textContent = "Admin requests could not be loaded.";
    }
}

async function updateAdminRequest(card) {
    const requestId = card.dataset.requestId;
    const status = card.querySelector(".admin-status-select")?.value;
    const adminNote = card.querySelector(".admin-note-input")?.value || "";

    if (!requestId || !status) return;

    adminMessage.textContent = "Saving admin update...";

    try {
        const res = await fetch("/admin/requests/update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                request_id: requestId,
                status,
                admin_note: adminNote,
            }),
        });

        const data = await res.json();
        adminMessage.textContent = data.message || "Request updated.";
        await loadAdminRequests();
    } catch (error) {
        console.error("Admin request update error:", error);
        adminMessage.textContent = "Admin update failed.";
    }
}

if (adminRequestList) {
    adminRequestList.addEventListener("click", (event) => {
        const button = event.target.closest(".admin-update-btn");
        if (!button) return;
        const card = button.closest(".admin-request-card");
        if (!card) return;
        updateAdminRequest(card);
    });
}

loadAdminRequests();
