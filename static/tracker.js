
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
    var barCharts = {
        "water-bar": { field: "total_oz", label: "Total (fl oz)" },
        "steps-bar": { field: "total_steps", label: "Steps" },
        "nutrition-bar": { field: "total_calories", label: "Calories (kcal)" }
    };
    var barConfig = barCharts[kind];
    var isBar = Boolean(barConfig);

    var labels = points.map(function (point) {
        return new Date(point.date + "T00:00:00").toLocaleDateString(undefined, {
            month: "short",
            day: "numeric"
        });
    });

    var dataset = isBar
        ? {
            label: barConfig.label,
            data: points.map(function (point) { return point[barConfig.field]; }),
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