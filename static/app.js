/* -------------------------------------------------------------
 * FLUXETL DATA PIPELINE CONTROL ENGINE (static/app.js)
 * Coordinates SPA routing, live API polling, interactive chart
 * renderers, manual ETL executions, and status notification systems.
 * ------------------------------------------------------------- */

document.addEventListener("DOMContentLoaded", () => {
    // Initialize Lucide Icons
    if (window.lucide) {
        window.lucide.createIcons();
    }

    // --- GLOBAL STATE ---
    let chartHistory = null;
    let chartProduct = null;
    let chartErrors = null;
    
    // Auto-refresh interval ID (polls every 30s)
    let statsPollInterval = null;

    // --- DOM SELECTORS ---
    const btnTrigger = document.getElementById("btn-trigger-pipeline");
    const btnExport = document.getElementById("btn-export-csv");
    const toastContainer = document.getElementById("toast-container");

    // Navigation buttons
    const navItems = document.querySelectorAll(".nav-item");
    const sections = document.querySelectorAll(".dashboard-section");
    const linkViewAllRuns = document.getElementById("link-view-all-runs");

    // --- SPA NAV ROUTING ---
    function navigateToSection(targetId) {
        sections.forEach(sec => {
            if (sec.id === `section-${targetId}`) {
                sec.classList.add("active");
            } else {
                sec.classList.remove("active");
            }
        });

        navItems.forEach(item => {
            if (item.id === `btn-nav-${targetId}`) {
                item.classList.add("active");
            } else {
                item.classList.remove("active");
            }
        });

        // Trigger updates when entering specific sections
        if (targetId === "overview") {
            refreshDashboardData();
        } else if (targetId === "runs") {
            fetchRuns();
        } else if (targetId === "errors") {
            fetchErrors();
        }
    }

    navItems.forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            const targetId = item.id.replace("btn-nav-", "");
            navigateToSection(targetId);
        });
    });

    if (linkViewAllRuns) {
        linkViewAllRuns.addEventListener("click", (e) => {
            e.preventDefault();
            navigateToSection("history");
        });
    }

    // --- TOAST NOTIFICATIONS ---
    function showToast(title, message, type = "info") {
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        
        let iconName = "info";
        if (type === "success") iconName = "check-circle";
        if (type === "error") iconName = "alert-triangle";
        
        toast.innerHTML = `
            <i data-lucide="${iconName}"></i>
            <div class="toast-content">
                <h4>${title}</h4>
                <p>${message}</p>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        if (window.lucide) {
            window.lucide.createIcons({ attrs: { class: 'lucide' } });
        }
        
        // Auto remove toast
        setTimeout(() => {
            toast.style.animation = "slideIn 0.3s ease reverse";
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    // --- DYNAMIC DATA FORMATTERS ---
    function formatCurrency(value) {
        return new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: "USD"
        }).format(value);
    }

    function formatDateTime(isoString) {
        if (!isoString) return "-";
        const date = new Date(isoString);
        return date.toLocaleString("en-US", {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit"
        });
    }

    function calculateDuration(startStr, endStr) {
        if (!startStr || !endStr) return "-";
        const start = new Date(startStr);
        const end = new Date(endStr);
        const diffMs = end - start;
        return `${(diffMs / 1000).toFixed(2)}s`;
    }

    // --- API HANDLERS ---

    // Fetch KPI Stats
    async function fetchStats() {
        try {
            const res = await fetch("/api/dashboard/stats");
            if (!res.ok) throw new Error("Failed to load KPI statistics");
            const data = await res.json();
            
            // Render KPI values
            document.getElementById("stat-total-sales").innerText = formatCurrency(data.total_sales);
            document.getElementById("stat-orders-count").innerText = `${data.total_orders} Valid Orders`;
            document.getElementById("stat-avg-order-val").innerText = formatCurrency(data.avg_order_value);
            document.getElementById("stat-pipeline-health").innerText = `${data.pipeline_health.success_rate}%`;
            document.getElementById("stat-total-runs").innerText = `${data.pipeline_health.total_runs} Total Syncs`;
            document.getElementById("stat-quality-rate").innerText = `${data.pipeline_health.data_quality_rate}%`;
            
            // Calculate total rejected records across last run logs to show in card
            const lastRun = data.last_run;
            if (lastRun) {
                document.getElementById("stat-rejected-count").innerText = `${lastRun.records_rejected} Rejected (Last Run)`;
            } else {
                document.getElementById("stat-rejected-count").innerText = "0 Rejected Records";
            }
        } catch (err) {
            console.error("Error fetching stats:", err);
            showToast("Stats Fetch Error", err.message, "error");
        }
    }

    // Fetch Runs Logs
    async function fetchRuns() {
        try {
            const res = await fetch("/api/pipeline/runs");
            if (!res.ok) throw new Error("Failed to load pipeline run logs");
            const runs = await res.json();
            
            const recentBody = document.getElementById("table-recent-runs-body");
            const fullBody = document.getElementById("table-full-runs-body");
            
            // Clear contents
            if (recentBody) recentBody.innerHTML = "";
            if (fullBody) fullBody.innerHTML = "";
            
            // Populate
            runs.forEach((run, index) => {
                const badgeClass = run.status.toLowerCase();
                const duration = calculateDuration(run.start_time, run.end_time);
                
                // Build row markup
                const rowHtml = `
                    <tr>
                        <td class="mono-text">${run.run_id}</td>
                        <td><span class="status-badge ${badgeClass}">${run.status}</span></td>
                        <td>${formatDateTime(run.start_time)}</td>
                        <td>${run.records_fetched}</td>
                        <td>${run.records_inserted}</td>
                        <td>${run.records_rejected}</td>
                    </tr>
                `;
                
                // Only put top 5 in overview preview table
                if (index < 5 && recentBody) {
                    recentBody.innerHTML += rowHtml;
                }
                
                // Put all in full table
                if (fullBody) {
                    const errorMsg = run.error_message ? `<span class="error-badge">${run.error_message}</span>` : '<span class="text-muted">-</span>';
                    fullBody.innerHTML += `
                        <tr>
                            <td class="mono-text">${run.run_id}</td>
                            <td>${formatDateTime(run.start_time)}</td>
                            <td>${duration}</td>
                            <td><span class="status-badge ${badgeClass}">${run.status}</span></td>
                            <td>${run.records_fetched}</td>
                            <td>${run.records_inserted}</td>
                            <td>${run.records_rejected}</td>
                            <td style="max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${run.error_message || ''}">${errorMsg}</td>
                        </tr>
                    `;
                }
            });
            
            if (runs.length === 0) {
                const emptyRow = `<tr><td colspan="6" style="text-align: center; color: var(--color-text-muted);">No pipeline sync logs available.</td></tr>`;
                if (recentBody) recentBody.innerHTML = emptyRow;
                if (fullBody) fullBody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--color-text-muted);">No pipeline sync logs available.</td></tr>`;
            }
        } catch (err) {
            console.error("Error fetching runs:", err);
            showToast("Log Sync Error", err.message, "error");
        }
    }

    // Fetch Validation Errors
    async function fetchErrors() {
        try {
            const res = await fetch("/api/pipeline/validation-errors");
            if (!res.ok) throw new Error("Failed to load validation error history");
            const errors = await res.json();
            
            const body = document.getElementById("table-full-errors-body");
            if (!body) return;
            body.innerHTML = "";
            
            errors.forEach(err => {
                // Parse and build readable error tags
                let errorChips = "";
                if (Array.isArray(err.error_details)) {
                    errorChips = err.error_details.map(d => {
                        const path = d.loc ? d.loc.join(".") : "field";
                        return `<div class="error-badge"><strong>${path}</strong>: ${d.msg}</div>`;
                    }).join("");
                } else {
                    errorChips = `<div class="error-badge">${err.error_details}</div>`;
                }
                
                const rawRecordStr = JSON.stringify(err.raw_record);
                
                body.innerHTML += `
                    <tr>
                        <td>${formatDateTime(err.logged_at)}</td>
                        <td class="mono-text">${err.run_id}</td>
                        <td>${err.record_index + 1}</td>
                        <td class="raw-json-cell">${rawRecordStr}</td>
                        <td><div class="error-badge-container">${errorChips}</div></td>
                    </tr>
                `;
            });
            
            if (errors.length === 0) {
                body.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--color-text-muted);">No validation failures found. All ingested data has been 100% clean!</td></tr>`;
            }
        } catch (err) {
            console.error("Error fetching errors:", err);
            showToast("Error Logs Fetch Failed", err.message, "error");
        }
    }

    // Fetch Charts and Update Canvas Elements
    async function fetchCharts() {
        try {
            const res = await fetch("/api/dashboard/charts");
            if (!res.ok) throw new Error("Failed to load chart payloads");
            const chartsData = await res.json();
            
            // Style Config Helpers
            const fontConfig = {
                family: "'Inter', sans-serif",
                size: 11
            };
            const gridConfig = {
                color: "rgba(148, 163, 184, 0.06)",
                drawBorder: false
            };

            // 1. ETL History Chart
            const historyObj = chartsData.pipeline_history;
            const labels = historyObj.map(h => h.time);
            const insertedData = historyObj.map(h => h.inserted);
            const rejectedData = historyObj.map(h => h.rejected);
            
            if (chartHistory) chartHistory.destroy();
            chartHistory = new Chart(document.getElementById("chart-run-history"), {
                type: "bar",
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: "Valid Saved",
                            data: insertedData,
                            backgroundColor: "#10b981",
                            borderRadius: 4
                        },
                        {
                            label: "Errors Rejected",
                            data: rejectedData,
                            backgroundColor: "#f43f5e",
                            borderRadius: 4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: { stacked: true, grid: { display: false }, ticks: { font: fontConfig, color: "#94a3b8" } },
                        y: { stacked: true, grid: gridConfig, ticks: { font: fontConfig, color: "#94a3b8" } }
                    },
                    plugins: {
                        legend: { position: "top", labels: { font: fontConfig, color: "#f8fafc", boxWidth: 10 } }
                    }
                }
            });

            // 2. Product Share Chart
            const productObj = chartsData.product_distribution;
            const productNames = productObj.map(p => p.name);
            const productRevenues = productObj.map(p => p.revenue);
            
            if (chartProduct) chartProduct.destroy();
            chartProduct = new Chart(document.getElementById("chart-product-share"), {
                type: "doughnut",
                data: {
                    labels: productNames,
                    datasets: [{
                        data: productRevenues,
                        backgroundColor: ["#0ea5e9", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899"],
                        borderWidth: 2,
                        borderColor: "#0f172a"
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: "bottom",
                            labels: { font: fontConfig, color: "#f8fafc", boxWidth: 8, padding: 8 }
                        }
                    },
                    cutout: "70%"
                }
            });

            // 3. Error Breakdown Chart
            const errorObj = chartsData.error_breakdown;
            const errorLabels = errorObj.map(e => e.label);
            const errorCounts = errorObj.map(e => e.count);
            
            if (chartErrors) chartErrors.destroy();
            chartErrors = new Chart(document.getElementById("chart-error-breakdown"), {
                type: "polarArea",
                data: {
                    labels: errorLabels,
                    datasets: [{
                        data: errorCounts,
                        backgroundColor: ["rgba(244, 63, 94, 0.7)", "rgba(245, 158, 11, 0.7)", "rgba(139, 92, 246, 0.7)", "rgba(236, 72, 153, 0.7)"],
                        borderColor: "#0f172a",
                        borderWidth: 1.5
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        r: {
                            grid: { color: "rgba(255, 255, 255, 0.05)" },
                            angleLines: { color: "rgba(255, 255, 255, 0.05)" },
                            ticks: { display: false }
                        }
                    },
                    plugins: {
                        legend: {
                            position: "bottom",
                            labels: { font: fontConfig, color: "#f8fafc", boxWidth: 8, padding: 8 }
                        }
                    }
                }
            });
        } catch (err) {
            console.error("Error drawing charts:", err);
        }
    }

    // Refresh All Data Elements
    function refreshDashboardData() {
        fetchStats();
        fetchRuns();
        fetchCharts();
    }

    // --- PIPELINE CONTROLLER ACTIONS ---

    // Trigger pipeline run
    async function triggerPipelineRun() {
        // Disable button, show loading spinner state
        btnTrigger.classList.add("loading");
        btnTrigger.disabled = true;
        const origContent = btnTrigger.innerHTML;
        btnTrigger.innerHTML = `<i class="lucide-spinner" style="animation: spin 1s linear infinite; display: inline-block;">↻</i> Executing...`;
        
        showToast("ETL Pipeline Started", "Connecting to external API and fetching records...", "info");
        
        try {
            const response = await fetch("/api/pipeline/trigger", { method: "POST" });
            if (!response.ok) throw new Error("HTTP connection failed during sync.");
            
            const result = await response.json();
            
            if (result.status === "SUCCESS") {
                showToast(
                    "ETL Synced Successfully", 
                    `Ingested ${result.records_fetched} records. Loaded ${result.records_inserted} clean entries.`,
                    "success"
                );
            } else if (result.status === "PARTIAL") {
                showToast(
                    "ETL Partial Warning", 
                    `Synced ${result.records_inserted} records. Rejected ${result.records_rejected} errors. Check validation log.`,
                    "success" // use green for partial warning as data is still saved
                );
            } else {
                showToast(
                    "ETL Sync Failure", 
                    result.error || "Zero valid records processed.",
                    "error"
                );
            }
            
            // Refresh whatever page is active
            const activeSection = document.querySelector(".dashboard-section.active");
            if (activeSection.id === "section-overview") {
                refreshDashboardData();
            } else if (activeSection.id === "section-history") {
                fetchRuns();
            } else if (activeSection.id === "section-errors") {
                fetchErrors();
            }
            
        } catch (err) {
            console.error("Error triggering pipeline:", err);
            showToast("Sync Pipeline Failed", err.message, "error");
        } finally {
            // Restore button state
            btnTrigger.classList.remove("loading");
            btnTrigger.disabled = false;
            btnTrigger.innerHTML = origContent;
        }
    }

    // Bind triggers
    if (btnTrigger) {
        btnTrigger.addEventListener("click", triggerPipelineRun);
    }
    
    if (btnExport) {
        btnExport.addEventListener("click", () => {
            window.location.href = "/api/dashboard/export";
            showToast("CSV Download Initiated", "Downloading cleaned database snapshot...", "success");
        });
    }

    // --- INITIALIZATION ---
    // Start initial loading
    refreshDashboardData();
    
    // Set up auto polling every 30 seconds for background sync updates
    statsPollInterval = setInterval(() => {
        const activeSection = document.querySelector(".dashboard-section.active");
        if (activeSection && activeSection.id === "section-overview") {
            refreshDashboardData();
        }
    }, 30000);
});

// Inline simple spinner animation style injection
const styleSheet = document.createElement("style");
styleSheet.innerText = `
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
`;
document.head.appendChild(styleSheet);
