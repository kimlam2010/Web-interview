/**
 * Main JavaScript for Mekong Recruitment System
 * Handles common functionality across all pages
 */

// Global variables
let assessmentTimer = null;
let autoSaveInterval = null;
let isTabActive = true;

// Utility Functions
const Utils = {
    /**
     * Show notification message
     * @param {string} message - Message to display
     * @param {string} type - Type of notification (success, warning, error, info)
     * @param {number} duration - Duration in milliseconds
     */
    showNotification: function(message, type = 'info', duration = 5000) {
        const alertClass = `alert-${type}`;
        const alertHtml = `
            <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        const container = document.querySelector('.notifications-container') || document.body;
        const alertElement = document.createElement('div');
        alertElement.innerHTML = alertHtml;
        container.appendChild(alertElement.firstElementChild);
        
        if (duration > 0) {
            setTimeout(() => {
                const alert = container.querySelector('.alert');
                if (alert) {
                    alert.remove();
                }
            }, duration);
        }
    },

    /**
     * Format time in MM:SS format
     * @param {number} seconds - Total seconds
     * @returns {string} Formatted time
     */
    formatTime: function(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
    },

    /**
     * Debounce function to limit function calls
     * @param {Function} func - Function to debounce
     * @param {number} wait - Wait time in milliseconds
     * @returns {Function} Debounced function
     */
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * Validate email format
     * @param {string} email - Email to validate
     * @returns {boolean} Is valid email
     */
    isValidEmail: function(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    },

    /**
     * Sanitize HTML content
     * @param {string} html - HTML content to sanitize
     * @returns {string} Sanitized HTML
     */
    sanitizeHtml: function(html) {
        const div = document.createElement('div');
        div.textContent = html;
        return div.innerHTML;
    }
};

// Assessment Timer Management
const AssessmentTimer = {
    /**
     * Start assessment timer
     * @param {number} duration - Duration in seconds
     * @param {Function} onExpire - Callback when timer expires
     */
    start: function(duration, onExpire) {
        let timeLeft = duration;
        const timerElement = document.getElementById('assessment-timer');
        
        if (!timerElement) return;
        
        const updateTimer = () => {
            if (timeLeft <= 0) {
                this.stop();
                if (onExpire) onExpire();
                return;
            }
            
            timerElement.textContent = Utils.formatTime(timeLeft);
            
            // Change color when time is running low
            if (timeLeft <= 300) { // 5 minutes
                timerElement.classList.add('text-danger');
            } else if (timeLeft <= 600) { // 10 minutes
                timerElement.classList.add('text-warning');
            }
            
            timeLeft--;
        };
        
        updateTimer();
        assessmentTimer = setInterval(updateTimer, 1000);
    },

    /**
     * Stop assessment timer
     */
    stop: function() {
        if (assessmentTimer) {
            clearInterval(assessmentTimer);
            assessmentTimer = null;
        }
    },

    /**
     * Pause assessment timer
     */
    pause: function() {
        if (assessmentTimer) {
            clearInterval(assessmentTimer);
            assessmentTimer = null;
        }
    },

    /**
     * Resume assessment timer
     */
    resume: function() {
        if (!assessmentTimer) {
            this.start();
        }
    }
};

// Auto-save functionality
const AutoSave = {
    /**
     * Start auto-save for assessment
     * @param {Function} saveFunction - Function to call for saving
     * @param {number} interval - Interval in milliseconds
     */
    start: function(saveFunction, interval = 30000) { // 30 seconds
        autoSaveInterval = setInterval(saveFunction, interval);
    },

    /**
     * Stop auto-save
     */
    stop: function() {
        if (autoSaveInterval) {
            clearInterval(autoSaveInterval);
            autoSaveInterval = null;
        }
    },

    /**
     * Save assessment progress
     */
    saveProgress: function() {
        const form = document.getElementById('assessment-form');
        if (!form) return;

        const formData = new FormData(form);
        const answers = {};
        
        // Collect all answers
        formData.forEach((value, key) => {
            if (key.startsWith('answer_')) {
                answers[key] = value;
            }
        });

        // Send to server
        fetch('/assessment/api/save-progress', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
            },
            body: JSON.stringify({
                answers: answers,
                timestamp: new Date().toISOString()
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('Progress saved successfully');
            } else {
                console.error('Failed to save progress:', data.error);
            }
        })
        .catch(error => {
            console.error('Error saving progress:', error);
        });
    }
};

// Tab switching detection
const TabMonitor = {
    /**
     * Initialize tab switching detection
     */
    init: function() {
        document.addEventListener('visibilitychange', this.handleVisibilityChange);
        window.addEventListener('focus', this.handleFocus);
        window.addEventListener('blur', this.handleBlur);
    },

    /**
     * Handle visibility change
     */
    handleVisibilityChange: function() {
        if (document.hidden) {
            isTabActive = false;
            TabMonitor.handleTabSwitch();
        } else {
            isTabActive = true;
        }
    },

    /**
     * Handle window focus
     */
    handleFocus: function() {
        isTabActive = true;
    },

    /**
     * Handle window blur
     */
    handleBlur: function() {
        isTabActive = false;
        TabMonitor.handleTabSwitch();
    },

    /**
     * Handle tab switching
     */
    handleTabSwitch: function() {
        if (!isTabActive) {
            Utils.showNotification('Tab switching detected! Please stay on this page during the assessment.', 'warning', 0);
        }
    }
};

// Form validation
const FormValidator = {
    /**
     * Validate form fields
     * @param {HTMLFormElement} form - Form to validate
     * @returns {boolean} Is form valid
     */
    validateForm: function(form) {
        let isValid = true;
        const requiredFields = form.querySelectorAll('[required]');
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                this.showFieldError(field, 'This field is required');
                isValid = false;
            } else {
                this.clearFieldError(field);
            }
        });

        // Email validation
        const emailFields = form.querySelectorAll('input[type="email"]');
        emailFields.forEach(field => {
            if (field.value && !Utils.isValidEmail(field.value)) {
                this.showFieldError(field, 'Please enter a valid email address');
                isValid = false;
            }
        });

        return isValid;
    },

    /**
     * Show field error
     * @param {HTMLElement} field - Field element
     * @param {string} message - Error message
     */
    showFieldError: function(field, message) {
        field.classList.add('is-invalid');
        
        let errorElement = field.parentNode.querySelector('.invalid-feedback');
        if (!errorElement) {
            errorElement = document.createElement('div');
            errorElement.className = 'invalid-feedback';
            field.parentNode.appendChild(errorElement);
        }
        errorElement.textContent = message;
    },

    /**
     * Clear field error
     * @param {HTMLElement} field - Field element
     */
    clearFieldError: function(field) {
        field.classList.remove('is-invalid');
        const errorElement = field.parentNode.querySelector('.invalid-feedback');
        if (errorElement) {
            errorElement.remove();
        }
    }
};

// Data table functionality
const DataTable = {
    /**
     * Initialize data table
     * @param {string} tableId - Table ID
     */
    init: function(tableId) {
        const table = document.getElementById(tableId);
        if (!table) return;

        // Add search functionality
        const searchInput = document.createElement('input');
        searchInput.type = 'text';
        searchInput.className = 'form-control mb-3';
        searchInput.placeholder = 'Search...';
        table.parentNode.insertBefore(searchInput, table);

        searchInput.addEventListener('input', Utils.debounce(function() {
            DataTable.filterTable(table, this.value);
        }, 300));
    },

    /**
     * Filter table rows
     * @param {HTMLTableElement} table - Table element
     * @param {string} searchTerm - Search term
     */
    filterTable: function(table, searchTerm) {
        const rows = table.querySelectorAll('tbody tr');
        const term = searchTerm.toLowerCase();

        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(term) ? '' : 'none';
        });
    }
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tab monitoring
    TabMonitor.init();

    // Initialize data tables
    const tables = document.querySelectorAll('.data-table');
    tables.forEach(table => {
        DataTable.init(table.id);
    });

    // Initialize form validation
    const forms = document.querySelectorAll('form[data-validate]');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!FormValidator.validateForm(this)) {
                e.preventDefault();
                Utils.showNotification('Please fix the errors in the form.', 'error');
            }
        });
    });

    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-save for assessment pages
    if (document.getElementById('assessment-form')) {
        AutoSave.start(AutoSave.saveProgress);
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    AssessmentTimer.stop();
    AutoSave.stop();
}); 