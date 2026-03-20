// Global Notification System for NexusLink
(function() {
    function initNotifications() {
        const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const url = `${proto}://${window.location.host}/ws/notifications/`;
        const socket = new WebSocket(url);

        socket.onmessage = function(e) {
            const data = JSON.parse(e.data);
            if (data.type === 'notification_update') {
                updateBadge(data.category, data.count_update);
            }
        };

        socket.onclose = function() {
            console.warn("Notification socket closed. Reconnecting in 5s...");
            setTimeout(initNotifications, 5000);
        };
    }

    function updateBadge(category, delta) {
        const id = category === 'message' ? 'unread-msg-badge' : 'pending-follow-badge';
        const badge = document.getElementById(id);
        if (!badge) return;

        let current = parseInt(badge.textContent) || 0;
        let newCount = current + delta;
        
        if (newCount > 0) {
            badge.textContent = newCount;
            badge.classList.remove('hidden');
            // Subtle pulse animation
            badge.animate([
                { transform: 'scale(1)' },
                { transform: 'scale(1.3)' },
                { transform: 'scale(1)' }
            ], { duration: 300 });
        } else {
            badge.classList.add('hidden');
        }
    }

    // Initialize if user is logged in (check for a specific nav element)
    if (document.querySelector('.nav-actions .user-avatar-nav')) {
        initNotifications();
    }
})();
