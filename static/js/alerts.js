document.addEventListener('DOMContentLoaded', () => {
    const bell = document.getElementById('notificationBell');
    if (!bell) {
        return;
    }

    bell.addEventListener('click', () => {
        fetch('/api/alerts')
            .then((response) => response.json())
            .then((payload) => {
                const count = payload.total || 0;
                showToast(
                    'Incident Queue',
                    `Alert queue contains ${count} incident${count === 1 ? '' : 's'}.`
                );
            })
            .catch(() => showToast('Incident Queue', 'Unable to load alerts right now.'));
    });
});
