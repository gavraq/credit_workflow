// Credit Workflow Application - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Enable all tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Enable all popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    const popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
    
    // Handle notification read status
    const notificationLinks = document.querySelectorAll('.notification-item');
    notificationLinks.forEach(function(link) {
        link.addEventListener('click', function(event) {
            const notificationId = this.dataset.notificationId;
            if (notificationId) {
                fetch(`/notifications/${notificationId}/mark-read/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => {
                    if (response.ok) {
                        this.classList.remove('fw-bold');
                        updateNotificationCount();
                    }
                });
            }
        });
    });
    
    // Dismiss notifications
    const dismissButtons = document.querySelectorAll('.notification-dismiss');
    dismissButtons.forEach(function(button) {
        button.addEventListener('click', function(event) {
            event.preventDefault();
            const notificationId = this.dataset.notificationId;
            const notificationItem = this.closest('.notification-item');
            
            if (notificationId && notificationItem) {
                fetch(`/notifications/${notificationId}/dismiss/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => {
                    if (response.ok) {
                        notificationItem.remove();
                        updateNotificationCount();
                    }
                });
            }
        });
    });
    
    // Document upload preview
    const fileInput = document.getElementById('file');
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            const fileNameElement = document.getElementById('file-name');
            if (fileNameElement) {
                fileNameElement.textContent = this.files[0] ? this.files[0].name : 'No file selected';
            }
        });
    }
    
    // Confirm actions with data-confirm attribute
    const confirmButtons = document.querySelectorAll('[data-confirm]');
    confirmButtons.forEach(function(button) {
        button.addEventListener('click', function(event) {
            if (!confirm(this.dataset.confirm)) {
                event.preventDefault();
            }
        });
    });
    
    // Update notification count function
    function updateNotificationCount() {
        const unreadCount = document.querySelectorAll('.notification-item.fw-bold').length;
        const countElement = document.querySelector('.notification-count');
        
        if (countElement) {
            if (unreadCount > 0) {
                countElement.innerHTML = `<span class="badge rounded-pill bg-danger">${unreadCount}</span>`;
            } else {
                countElement.innerHTML = '';
            }
        }
    }
    
    // Helper function to get CSRF token
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
