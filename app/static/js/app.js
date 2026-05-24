document.addEventListener('DOMContentLoaded', function() {
    // Listen for HTMX events to show toast notifications
    document.body.addEventListener('showToast', function(event) {
        showToast(event.detail.message, event.detail.type || 'success');
    });

    // Handle HTMX afterSwap for flash messages
    document.body.addEventListener('htmx:afterSwap', function(event) {
        var header = event.detail.xhr.getResponseHeader('HX-Trigger');
        if (header) {
            try {
                var triggers = JSON.parse(header);
                if (triggers.showToast) {
                    showToast(triggers.showToast.message, triggers.showToast.type);
                }
            } catch(e) {
                // Not JSON, ignore
            }
        }
    });
});

function showToast(message, type) {
    type = type || 'success';
    var container = document.getElementById('toast-container');
    var iconMap = {
        'success': 'bi-check-circle-fill',
        'danger': 'bi-exclamation-triangle-fill',
        'warning': 'bi-exclamation-circle-fill',
        'info': 'bi-info-circle-fill'
    };
    var bgMap = {
        'success': 'text-bg-success',
        'danger': 'text-bg-danger',
        'warning': 'text-bg-warning',
        'info': 'text-bg-info'
    };

    var toastEl = document.createElement('div');
    toastEl.className = 'toast align-items-center ' + (bgMap[type] || 'text-bg-info');
    toastEl.setAttribute('role', 'alert');
    toastEl.innerHTML =
        '<div class="d-flex">' +
            '<div class="toast-body">' +
                '<i class="bi ' + (iconMap[type] || 'bi-info-circle-fill') + ' me-2"></i>' +
                message +
            '</div>' +
            '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>' +
        '</div>';

    container.appendChild(toastEl);
    var toast = new bootstrap.Toast(toastEl, { delay: 3000 });
    toast.show();
    toastEl.addEventListener('hidden.bs.toast', function() {
        toastEl.remove();
    });
}

function getScoreClass(score) {
    if (score === null || score === undefined) return '';
    if (score >= 7) return 'score-high';
    if (score >= 4) return 'score-medium';
    return 'score-low';
}
