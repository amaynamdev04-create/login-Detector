const chartRegistry = {};

function chartPalette() {
    const styles = getComputedStyle(document.documentElement);
    return {
        text: styles.getPropertyValue('--text').trim(),
        muted: styles.getPropertyValue('--muted').trim(),
        border: styles.getPropertyValue('--border').trim(),
        accent: styles.getPropertyValue('--accent').trim(),
        success: styles.getPropertyValue('--success').trim(),
        danger: styles.getPropertyValue('--danger').trim(),
        warning: styles.getPropertyValue('--warning').trim()
    };
}

function destroyChart(id) {
    if (chartRegistry[id]) {
        chartRegistry[id].destroy();
    }
}

function createChart(id, config) {
    const canvas = document.getElementById(id);
    if (!canvas) {
        return null;
    }
    destroyChart(id);
    chartRegistry[id] = new Chart(canvas, config);
    return chartRegistry[id];
}

function sharedChartOptions() {
    const palette = chartPalette();
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: {
                    color: palette.text
                }
            }
        },
        scales: {
            x: {
                ticks: { color: palette.muted },
                grid: { color: palette.border }
            },
            y: {
                ticks: { color: palette.muted },
                grid: { color: palette.border }
            }
        }
    };
}
