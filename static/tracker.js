// Quick-add buttons fill in a form field; the user still presses Save.
document.querySelectorAll("button[data-amount]").forEach(function (button) {
    button.addEventListener("click", function () {
        var input = button.form.elements[button.dataset.target];
        input.value = button.dataset.amount;
        input.focus();
    });
});

// Draw the page's trend chart from the JSON embedded next to it.
(function () {
    var dataElement = document.getElementById("chart-data");
    var canvas = document.getElementById("trend-chart");

    if (!dataElement || !canvas || !window.Chart) {
        return;
    }

    var points = JSON.parse(dataElement.textContent);
    var styles = getComputedStyle(document.documentElement);
    var accent = styles.getPropertyValue("--accent").trim();
    var muted = styles.getPropertyValue("--muted").trim();
    var grid = styles.getPropertyValue("--border").trim();
    var kind = dataElement.dataset.chart;
    var isBar = kind === "water-bar" || kind === "steps-bar";
    var barField = kind === "steps-bar" ? "total_steps" : "total_oz";
    var barLabel = kind === "steps-bar" ? "Steps" : "Total (fl oz)";

    var labels = points.map(function (point) {
        return new Date(point.date + "T00:00:00").toLocaleDateString(undefined, {
            month: "short",
            day: "numeric"
        });
    });

    var dataset = isBar
        ? {
            label: barLabel,
            data: points.map(function (point) { return point[barField]; }),
            backgroundColor: accent,
            borderRadius: 4
        }
        : {
            label: "Weight (lb)",
            data: points.map(function (point) { return point.weight_lb; }),
            borderColor: accent,
            backgroundColor: accent,
            tension: 0.25,
            pointRadius: 3
        };

    new window.Chart(canvas, {
        type: isBar ? "bar" : "line",
        data: { labels: labels, datasets: [dataset] },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { color: muted } },
                y: {
                    beginAtZero: isBar,
                    grid: { color: grid },
                    ticks: { color: muted }
                }
            }
        }
    });
})();
