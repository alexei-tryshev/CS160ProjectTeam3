// Quick-add buttons fill in a form field; the user still presses Save.
document.querySelectorAll("button[data-amount]").forEach(function (button) {
    button.addEventListener("click", function () {
        var input = button.form.elements[button.dataset.target];
        input.value = button.dataset.amount;
        input.focus();
    });
});

// Shared visual settings for the page charts.
function chartTheme() {
    var styles = getComputedStyle(document.documentElement);

    return {
        accent: styles.getPropertyValue("--accent").trim() || "#31b47a",
        muted: styles.getPropertyValue("--muted").trim() || "#6a7d73",
        grid: styles.getPropertyValue("--border").trim() || "#dce9e0",
        dark: styles.getPropertyValue("--text").trim() || "#14251d",
        blue: styles.getPropertyValue("--blue").trim() || "#4b8fd8",
        amber: styles.getPropertyValue("--amber").trim() || "#e9a649"
    };
}

function chartOptions(theme, showLegend) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { intersect: false, mode: "index" },
        plugins: {
            legend: {
                display: showLegend,
                labels: {
                    usePointStyle: true,
                    pointStyle: "circle",
                    padding: 18,
                    color: theme.muted,
                    font: { size: 11, weight: "600" }
                }
            },
            tooltip: {
                backgroundColor: theme.dark,
                titleColor: "#ffffff",
                bodyColor: "#d9f4e4",
                padding: 12,
                cornerRadius: 10,
                displayColors: true,
                boxPadding: 5
            }
        },
        scales: {
            x: {
                grid: { display: false },
                border: { display: false },
                ticks: {
                    color: theme.muted,
                    font: { size: 10, weight: "600" },
                    maxRotation: 0
                }
            },
            y: {
                border: { display: false },
                grid: { color: theme.grid },
                ticks: {
                    color: theme.muted,
                    font: { size: 10, weight: "600" },
                    padding: 8
                }
            }
        }
    };
}

// Draw the page's trend chart from the JSON embedded next to it.
(function () {
    var dataElement = document.getElementById("chart-data");
    var canvas = document.getElementById("trend-chart");
    if (!dataElement || !canvas || !window.Chart) {
        return;
    }

    var points = JSON.parse(dataElement.textContent);
    var theme = chartTheme();
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
            backgroundColor: theme.accent,
            hoverBackgroundColor: "#208258",
            borderRadius: 7,
            borderSkipped: false,
            maxBarThickness: 30
        }
        : {
            label: "Weight (lb)",
            data: points.map(function (point) { return point.weight_lb; }),
            borderColor: theme.accent,
            backgroundColor: "rgba(49, 180, 122, 0.14)",
            fill: true,
            tension: 0.35,
            pointRadius: 3,
            pointHoverRadius: 6,
            pointBackgroundColor: "#ffffff",
            pointBorderWidth: 2,
            pointBorderColor: theme.accent
        };

    var options = chartOptions(theme, false);
    options.scales.y.beginAtZero = isBar;

    new window.Chart(canvas, {
        type: isBar ? "bar" : "line",
        data: { labels: labels, datasets: [dataset] },
        options: options
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
    var theme = chartTheme();

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
            backgroundColor: theme.accent,
            borderRadius: 6,
            borderSkipped: false,
            maxBarThickness: 22
        },
        {
            label: "Carbohydrates (g)",
            data: points.map(function (point) { return point.carbs_g; }),
            backgroundColor: theme.blue,
            borderRadius: 6,
            borderSkipped: false,
            maxBarThickness: 22
        },
        {
            label: "Fat (g)",
            data: points.map(function (point) { return point.fat_g; }),
            backgroundColor: theme.amber,
            borderRadius: 6,
            borderSkipped: false,
            maxBarThickness: 22
        }
    ];

    var options = chartOptions(theme, true);
    options.scales.y.beginAtZero = true;

    new window.Chart(canvas, {
        type: "bar",
        data: { labels: labels, datasets: datasets },
        options: options
    });
})();
