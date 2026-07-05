function dashboardPage() {
    return {
        refreshStats() {
            window.location.reload();
        }
    };
}

function renderDashboardCharts() {
    const dashboardDataTag = document.getElementById('dashboard-data');
    if (dashboardDataTag) {
        const dashboardData = JSON.parse(dashboardDataTag.textContent);
        const palette = chartPalette();

        createChart('attackTimelineChart', {
            type: 'line',
            data: {
                labels: dashboardData.hourly_activity.map((item) => item.label),
                datasets: [{
                    label: 'Hourly activity',
                    data: dashboardData.hourly_activity.map((item) => item.count),
                    borderColor: palette.accent,
                    backgroundColor: `${palette.accent}33`,
                    fill: true,
                    tension: 0.3
                }]
            },
            options: sharedChartOptions()
        });

        createChart('topAttackersChart', {
            type: 'bar',
            data: {
                labels: dashboardData.top_attackers.map((item) => item.label),
                datasets: [{
                    label: 'Failed attempts',
                    data: dashboardData.top_attackers.map((item) => item.count),
                    backgroundColor: [palette.danger, palette.warning, palette.accent, palette.success, palette.text]
                }]
            },
            options: sharedChartOptions()
        });

        createChart('topUsersChart', {
            type: 'doughnut',
            data: {
                labels: dashboardData.top_users.map((item) => item.label),
                datasets: [{
                    data: dashboardData.top_users.map((item) => item.count),
                    backgroundColor: [palette.accent, palette.success, palette.warning, palette.danger, palette.text]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { color: palette.text }
                    }
                }
            }
        });
    }

    const analyticsTag = document.getElementById('analytics-data');
    if (analyticsTag) {
        const analyticsData = JSON.parse(analyticsTag.textContent);
        const palette = chartPalette();

        createChart('statusChart', {
            type: 'pie',
            data: {
                labels: analyticsData.status_breakdown.labels,
                datasets: [{
                    data: analyticsData.status_breakdown.values,
                    backgroundColor: [palette.success, palette.danger]
                }]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });

        createChart('riskDistributionChart', {
            type: 'bar',
            data: {
                labels: analyticsData.risk_distribution.labels,
                datasets: [{
                    label: 'Events',
                    data: analyticsData.risk_distribution.values,
                    backgroundColor: palette.accent
                }]
            },
            options: sharedChartOptions()
        });

        createChart('attackSourcesChart', {
            type: 'polarArea',
            data: {
                labels: analyticsData.top_attack_sources.labels,
                datasets: [{
                    data: analyticsData.top_attack_sources.values,
                    backgroundColor: [palette.danger, palette.warning, palette.accent, palette.success, palette.text]
                }]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });

        createChart('hourlyTrendChart', {
            type: 'line',
            data: {
                labels: analyticsData.hourly_trend.labels,
                datasets: [{
                    label: 'Hourly events',
                    data: analyticsData.hourly_trend.values,
                    borderColor: palette.success,
                    backgroundColor: `${palette.success}33`,
                    fill: true,
                    tension: 0.25
                }]
            },
            options: sharedChartOptions()
        });

        createChart('siteSourcesChart', {
            type: 'bar',
            data: {
                labels: analyticsData.site_sources.labels,
                datasets: [{
                    label: 'Events by source',
                    data: analyticsData.site_sources.values,
                    backgroundColor: palette.warning
                }]
            },
            options: sharedChartOptions()
        });

        createChart('countryDistributionChart', {
            type: 'bar',
            data: {
                labels: analyticsData.country_distribution.labels,
                datasets: [{
                    label: 'Events by country',
                    data: analyticsData.country_distribution.values,
                    backgroundColor: palette.accent
                }]
            },
            options: sharedChartOptions()
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-counter]').forEach((node) => {
        const target = Number(node.getAttribute('data-counter'));
        if (Number.isNaN(target)) {
            return;
        }
        let value = 0;
        const step = Math.max(1, Math.ceil(target / 20));
        const interval = window.setInterval(() => {
            value += step;
            if (value >= target) {
                node.textContent = target;
                window.clearInterval(interval);
                return;
            }
            node.textContent = value;
        }, 24);
    });

    renderDashboardCharts();
});

document.addEventListener('themechange', () => {
    renderDashboardCharts();
});
