function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem('lam-theme', theme);
    document.dispatchEvent(new CustomEvent('themechange', { detail: { theme } }));
}

function appShell() {
    return {
        sidebarCollapsed: false,
        theme: document.documentElement.dataset.theme || 'dark',
        toggleTheme() {
            this.theme = this.theme === 'dark' ? 'light' : 'dark';
            applyTheme(this.theme);
        }
    };
}

document.addEventListener('DOMContentLoaded', () => {
    const timeNode = document.getElementById('currentTime');
    if (timeNode) {
        const renderTime = () => {
            timeNode.textContent = new Intl.DateTimeFormat(undefined, {
                dateStyle: 'medium',
                timeStyle: 'medium'
            }).format(new Date());
        };
        renderTime();
        window.setInterval(renderTime, 1000);
    }

    const privateIpField = document.getElementById('privateIpField');
    if (privateIpField) {
        privateIpField.value = '';
    }
});

function showToast(title, message) {
    const root = document.getElementById('toastRoot');
    if (!root) {
        return;
    }
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `<strong>${title}</strong><p>${message}</p>`;
    root.appendChild(toast);
    window.setTimeout(() => {
        toast.remove();
    }, 3200);
}
