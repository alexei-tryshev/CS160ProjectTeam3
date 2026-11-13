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

// Draw the daily macronutrient breakdown chart when present on the page.
(function () {
    var dataElement = document.getElementById("macro-chart-data");
    var canvas = document.getElementById("macro-chart");
    if (!dataElement || !canvas || !window.Chart) {
        return;
    }

    var points = JSON.parse(dataElement.textContent);
    var styles = getComputedStyle(document.documentElement);
    var accent = styles.getPropertyValue("--accent").trim() || "#31805f";
    var muted = styles.getPropertyValue("--muted").trim();
    var grid = styles.getPropertyValue("--border").trim();

    var labels = points.map(function (point) {
        return new Date(point.date + "T00:00:00").toLocaleDateString(undefined, {
            month: "short",
            day: "numeric"
        });
    });

    var datasets = [
        {
            label: "Protein (g)",
            data: points.map(function (point) { return point.protein_g; }),
            backgroundColor: accent,
            borderRadius: 4
        },
        {
            label: "Carbohydrates (g)",
            data: points.map(function (point) { return point.carbs_g; }),
            backgroundColor: "#2b6cb0",
            borderRadius: 4
        },
        {
            label: "Fat (g)",
            data: points.map(function (point) { return point.fat_g; }),
            backgroundColor: "#d97706",
            borderRadius: 4
        }
    ];

    new window.Chart(canvas, {
        type: "bar",
        data: { labels: labels, datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: true } },
            scales: {
                x: { grid: { display: false }, ticks: { color: muted } },
                y: {
                    beginAtZero: true,
                    grid: { color: grid },
                    ticks: { color: muted }
                }
            }
        }
    });
})();