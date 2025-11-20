let currentPage = 1;
let searchDebounceTimer = null;

function debounce(fn, wait = 300) {
    return (...args) => {
        if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
        searchDebounceTimer = setTimeout(() => fn(...args), wait);
    };
}

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("uploadBtn").addEventListener("click", uploadCSV);
    document.getElementById("fileInput").addEventListener("change", () => {
        const el = document.querySelector(".filepicker .filepicker-label");
        const f = document.getElementById("fileInput").files[0];
        el.textContent = f ? f.name : "Choose CSV...";
    });

    document.getElementById("searchBox").addEventListener("input", debounce(() => {
        currentPage = 1;
        loadProducts();
    }, 350));

    document.getElementById("activeFilter").addEventListener("change", () => { currentPage = 1; loadProducts(); });
    document.getElementById("perPageSelect").addEventListener("change", () => { currentPage = 1; loadProducts(); });

    document.getElementById("prevPageBtn").addEventListener("click", () => { if (currentPage > 1) { currentPage--; loadProducts(); } });
    document.getElementById("nextPageBtn").addEventListener("click", () => { currentPage++; loadProducts(); });

    document.getElementById("createProductBtn").addEventListener("click", () => openProductModal());
    document.getElementById("deleteAllBtn").addEventListener("click", handleDeleteAll);
    document.getElementById("manageWebhooksBtn").addEventListener("click", manageWebhooksPrompt);

    document.getElementById("modalCancelBtn").addEventListener("click", closeProductModal);
    document.getElementById("modalSaveBtn").addEventListener("click", saveProductFromModal);
    document.getElementById("modalBackdrop").addEventListener("click", closeProductModal);

    currentPage = 1;
    loadProducts();
});

async function uploadCSV() {
    const fileInput = document.getElementById("fileInput");
    const file = fileInput.files[0];
    if (!file) { alert("Please select a CSV file"); return; }

    const progressEl = document.getElementById("progress");
    progressEl.innerHTML = "Uploading…";

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch("/api/uploads/", { method: "POST", body: formData });
        if (!res.ok) {
            progressEl.textContent = "Upload failed: " + await res.text();
            return;
        }
        const data = await res.json();
        if (data.task_id) {
            progressEl.textContent = `Upload accepted — processing (task ${data.task_id})`;
            checkTaskStatus(data.task_id);
        } else {
            progressEl.textContent = "Upload failed: " + JSON.stringify(data);
        }
    } catch (err) {
        progressEl.textContent = "Upload error: " + err.message;
    }
}

async function checkTaskStatus(taskId) {
    const progressEl = document.getElementById("progress");

    if (!document.getElementById("progressBar")) {
        progressEl.innerHTML = "";
        const barWrapper = document.createElement("div");
        barWrapper.className = "progress-bar-wrapper";
        barWrapper.style = "border:1px solid #e6eefc; height:14px; border-radius:8px; background:#f3f4f6; overflow:hidden";
        const bar = document.createElement("div");
        bar.id = "progressBar";
        bar.style = "height:100%; width:0%; background:#0b5ed7; transition:width 300ms ease";
        barWrapper.appendChild(bar);
        progressEl.appendChild(barWrapper);

        const stage = document.createElement("div");
        stage.id = "progressStage";
        stage.style.marginTop = "8px";
        progressEl.appendChild(stage);

        const percent = document.createElement("div");
        percent.id = "progressPercent";
        percent.style.marginTop = "6px";
        progressEl.appendChild(percent);
    }

    const interval = setInterval(async () => {
        try {
            const res = await fetch(`/api/uploads/status/${taskId}`);
            if (!res.ok) {
                clearInterval(interval);
                document.getElementById("progressStage").textContent = `Status check failed: ${res.status}`;
                return;
            }
            const data = await res.json();
            const meta = data.result || {};
            const status = data.status || "";

            if (status === "STARTED" || meta.stage === "parsing") {
                document.getElementById("progressStage").textContent = meta.message || "Parsing CSV…";
                document.getElementById("progressBar").style.width = "6%";
                document.getElementById("progressPercent").textContent = "Parsing…";
            } else if (meta.stage === "parsed") {
                const total = meta.total ?? 0;
                document.getElementById("progressStage").textContent = `Parsed ${total} rows — preparing updates`;
                document.getElementById("progressBar").style.width = "12%";
                document.getElementById("progressPercent").textContent = `0% — 0 / ${total}`;
            } else if (meta.stage === "updating") {
                const total = meta.total ?? 0;
                const updated = meta.updated ?? 0;
                const pct = meta.percentage ?? Math.round((updated / Math.max(total, 1)) * 100);
                document.getElementById("progressStage").textContent = `Updating existing — ${updated} updated`;
                document.getElementById("progressBar").style.width = `${Math.min(pct, 90)}%`;
                document.getElementById("progressPercent").textContent = `${pct}% — ${updated} / ${total}`;
            } else if (meta.stage === "inserting") {
                const total = meta.total ?? 0;
                const updated = meta.updated ?? 0;
                const created = meta.created ?? 0;
                const processed = updated + created;
                const pct = meta.percentage ?? Math.round((processed / Math.max(total, 1)) * 100);
                document.getElementById("progressStage").textContent = `Inserting new — ${created} created`;
                document.getElementById("progressBar").style.width = `${Math.min(pct, 98)}%`;
                document.getElementById("progressPercent").textContent = `${pct}% — ${processed} / ${total}`;
            } else if (status === "SUCCESS") {
                clearInterval(interval);
                const created = data.result?.created ?? 0;
                const updated = data.result?.updated ?? 0;
                const total = data.result?.total ?? (created + updated);
                document.getElementById("progressStage").textContent = `Import complete — created: ${created}, updated: ${updated}`;
                document.getElementById("progressBar").style.width = `100%`;
                document.getElementById("progressPercent").textContent = `100% — ${total} / ${total}`;
                if (typeof loadProducts === "function") loadProducts();
            } else if (status === "FAILURE") {
                clearInterval(interval);
                document.getElementById("progressStage").textContent = `Import failed: ${meta.exc || JSON.stringify(meta)}`;
                document.getElementById("progressBar").style.width = "0%";
                document.getElementById("progressPercent").textContent = "Failed";
            } else {
                document.getElementById("progressStage").textContent = `Status: ${status} ${meta.message || ""}`;
            }
        } catch (err) {
            clearInterval(interval);
            document.getElementById("progressStage").textContent = "Status check error: " + err.message;
            document.getElementById("progressBar").style.width = "0%";
            document.getElementById("progressPercent").textContent = "Error";
        }
    }, 1200);
}

async function loadProducts() {
    const searchRaw = document.getElementById("searchBox").value || "";
    const search = encodeURIComponent(searchRaw);
    const perPage = parseInt(document.getElementById("perPageSelect").value || "20", 10);
    const activeFilter = document.getElementById("activeFilter").value;
    const activeParam = (activeFilter === "all") ? "" : `&active=${activeFilter}`;

    const res = await fetch(`/api/products?page=${currentPage}&per_page=${perPage}&search=${search}${activeParam}`);
    if (!res.ok) {
        console.error("Failed to load products", await res.text());
        return;
    }
    const products = await res.json();

    const tbody = document.getElementById("productsBody");
    tbody.innerHTML = "";

    products.forEach(p => {
        const tr = document.createElement("tr");
        if (!p.active) tr.classList.add("inactive");
        tr.innerHTML = `
      <td>${p.id ?? ""}</td>
      <td>${escapeHtml(p.sku ?? "")}</td>
      <td>${escapeHtml(p.name ?? "")}</td>
      <td>${escapeHtml(p.description ?? "")}</td>
      <td style="text-align:center;"><input type="checkbox" class="active-toggle" data-id="${p.id}" ${p.active ? "checked" : ""} /></td>
      <td class="action-buttons">
        <button data-id="${p.id}" class="btn small" data-action="edit">Edit</button>
        <button data-id="${p.id}" class="btn small danger" data-action="delete">Delete</button>
      </td>
    `;
        tbody.appendChild(tr);
    });

    document.querySelectorAll(".action-buttons button").forEach(btn => {
        btn.addEventListener("click", async (e) => {
            const id = e.currentTarget.getAttribute("data-id");
            const action = e.currentTarget.getAttribute("data-action");
            if (action === "edit") openProductModal(id);
            if (action === "delete") {
                if (!confirm("Delete product id " + id + "?")) return;
                await fetch(`/api/products/${id}`, { method: "DELETE" });
                loadProducts();
            }
        });
    });

    document.querySelectorAll(".active-toggle").forEach(chk => {
        chk.addEventListener("change", async (e) => {
            const id = e.currentTarget.getAttribute("data-id");
            const newVal = e.currentTarget.checked;
            const checkbox = e.currentTarget;
            const row = checkbox.closest("tr");

            checkbox.disabled = true;

            try {
                const res = await fetch(`/api/products/${id}`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ active: newVal })
                });

                if (!res.ok) {
                    checkbox.checked = !newVal;
                    const txt = await res.text();
                    alert("Failed to update active state: " + txt);
                } else {
                    if (newVal) {
                        row.classList.remove("inactive");
                    } else {
                        row.classList.add("inactive");
                    }
                }
            } catch (err) {
                checkbox.checked = !newVal;
                alert("Error updating active state: " + err.message);
            } finally {
                checkbox.disabled = false;
            }
        });
    });

    document.getElementById("currentPage").textContent = currentPage;
    document.getElementById("prevPageBtn").disabled = currentPage <= 1;
    document.getElementById("nextPageBtn").disabled = products.length < perPage;
}

function openProductModal(productId) {
    const modal = document.getElementById("productModal");
    const backdrop = document.getElementById("modalBackdrop");
    document.getElementById("modalProductId").value = productId || "";
    document.getElementById("modalTitle").textContent = productId ? "Edit Product" : "Create Product";
    document.getElementById("modalSku").disabled = !!productId;
    document.getElementById("modalSku").value = "";
    document.getElementById("modalName").value = "";
    document.getElementById("modalDescription").value = "";
    document.getElementById("modalActive").checked = true;

    if (productId) {
        fetch(`/api/products/${productId}`)
            .then(r => {
                if (!r.ok) throw new Error("Failed to load product");
                return r.json();
            })
            .then(p => {
                document.getElementById("modalSku").value = p.sku || "";
                document.getElementById("modalName").value = p.name || "";
                document.getElementById("modalDescription").value = p.description || "";
                document.getElementById("modalActive").checked = p.active ?? true;
            }).catch(err => alert(err.message));
    }

    modal.style.display = "block";
    modal.setAttribute("aria-hidden", "false");
    backdrop.style.display = "block";
}

function closeProductModal() {
    const modal = document.getElementById("productModal");
    const backdrop = document.getElementById("modalBackdrop");
    modal.style.display = "none";
    modal.setAttribute("aria-hidden", "true");
    backdrop.style.display = "none";
    document.getElementById("modalProductId").value = "";
}

async function saveProductFromModal() {
    const id = document.getElementById("modalProductId").value;
    const sku = document.getElementById("modalSku").value.trim();
    const name = document.getElementById("modalName").value.trim();
    const description = document.getElementById("modalDescription").value.trim();
    const active = document.getElementById("modalActive").checked;

    if (!sku || !name) return alert("SKU and Name are required");

    try {
        if (id) {
            const res = await fetch(`/api/products/${id}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name, description, active })
            });
            if (!res.ok) return alert("Update failed: " + await res.text());
        } else {
            const res = await fetch(`/api/products`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ sku, name, description })
            });
            if (!res.ok) return alert("Create failed: " + await res.text());
        }
        closeProductModal();
        loadProducts();
    } catch (err) {
        alert("Error saving product: " + err.message);
    }
}

async function handleDeleteAll() {
    if (!confirm("Are you sure? This will permanently delete ALL products. This cannot be undone.")) return;
    const progress = document.getElementById("progress");
    progress.textContent = "Requesting delete...";

    try {
        const res = await fetch("/api/products/delete-all", { method: "DELETE" });
        if (!res.ok) { progress.textContent = "Delete request failed: " + await res.text(); return; }
        const data = await res.json();
        if (data.task_id) {
            progress.textContent = "Delete accepted — processing (task " + data.task_id + ")";
            checkTaskStatus(data.task_id);
        } else {
            progress.textContent = "Delete request failed: " + JSON.stringify(data);
        }
    } catch (err) {
        progress.textContent = "Delete request error: " + err.message;
    }
}

async function manageWebhooksPrompt() {
    try {
        const res = await fetch("/api/webhooks");
        const whs = await res.json();
        let msg = "Webhooks:\n";
        whs.forEach(w => msg += `${w.id}: ${w.name || "(no name)"} [${w.event}] ${w.url} (enabled=${w.enabled})\n`);
        msg += "\nChoose: (c)reate, (t)est <id>, (d)elete <id>, (u)pdate <id>, (n)one";
        const action = prompt(msg);
        if (!action) return;
        if (action.startsWith("c")) {
            const name = prompt("Name:");
            const url = prompt("URL (https://...)");
            const event = prompt("Event (e.g. import.completed):");
            const enabled = confirm("Enable webhook?");
            if (!url || !event) return alert("URL and event required");
            const createRes = await fetch("/api/webhooks", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name, url, event, enabled })
            });
            alert(await createRes.text());
        } else if (action.startsWith("t")) {
            const id = (action.split(" ")[1]) || prompt("Webhook id to test:");
            if (!id) return;
            const payload = { test: true };
            const testRes = await fetch(`/api/webhooks/${id}/test`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            if (!testRes.ok) alert("Test failed: " + await testRes.text()); else alert("Test OK: " + await testRes.text());
        } else if (action.startsWith("d")) {
            const id = (action.split(" ")[1]) || prompt("Webhook id to delete:");
            if (!id) return;
            const delRes = await fetch(`/api/webhooks/${id}`, { method: "DELETE" });
            alert(await delRes.text());
        } else if (action.startsWith("u")) {
            const id = (action.split(" ")[1]) || prompt("Webhook id to update:");
            if (!id) return;
            const url = prompt("New URL (leave blank to keep):");
            const enabled = confirm("Enable webhook?");
            const updRes = await fetch(`/api/webhooks/${id}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url: url || undefined, enabled })
            });
            alert(await updRes.text());
        }
    } catch (err) {
        alert("Failed to manage webhooks: " + err.message);
    }
}

function escapeHtml(text) {
    if (!text) return "";
    return text.replace(/[&<>"'`]/g, (s) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;', '`': '&#96;' }[s]));
}