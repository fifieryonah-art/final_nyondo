/* ===================================
   FORM VALIDATION JAVASCRIPT
   Frontend validation utility for Nyondo Hardware
   =================================== */

class FormValidator {
    constructor(formSelector) {
        this.form = document.querySelector(formSelector);
        if (this.form) {
            this.form.addEventListener('submit', (e) => this.handleSubmit(e));
            this.attachFieldValidation();
        }
    }

    attachFieldValidation() {
        const inputs = this.form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('blur', () => this.validateField(input));
            input.addEventListener('change', () => this.validateField(input));
        });
    }

    validateField(field) {
        const value = field.value.trim();
        const fieldType = field.type;
        const isRequired = field.hasAttribute('required');
        const name = field.name || field.id;
        let errors = [];

        if (isRequired && !value) {
            errors.push(`${this.formatFieldName(name)} is required`);
        } else if (value) {
            switch (fieldType) {
                case 'email':
                    if (!this.isValidEmail(value)) {
                        errors.push(`Please enter a valid email address`);
                    }
                    break;
                case 'tel':
                    if (!this.isValidPhone(value)) {
                        errors.push(`Please enter a valid phone number`);
                    }
                    break;
                case 'number':
                    if (isNaN(value)) {
                        errors.push(`Please enter a valid number`);
                    }
                    break;
            }

            // Custom validation
            const customValidator = field.dataset.validate;
            if (customValidator) {
                const customErrors = this.runCustomValidation(customValidator, value, field);
                errors = errors.concat(customErrors);
            }
        }

        this.displayFieldError(field, errors);
        return errors.length === 0;
    }

    runCustomValidation(validator, value, field) {
        const errors = [];

        switch (validator) {
            case 'nin':
                if (!/^[A-Za-z0-9]{14}$/.test(value)) {
                    errors.push('Please enter a valid 14-character alphanumeric NIN');
                }
                break;
            case 'positive':
                if (parseFloat(value) <= 0) {
                    errors.push('Please enter a positive number');
                }
                break;
            case 'price':
                if (!/^\d+(\.\d{1,2})?$/.test(value) || parseFloat(value) <= 0) {
                    errors.push('Please enter a valid price');
                }
                break;
            case 'quantity':
                if (!/^\d+$/.test(value) || parseInt(value) <= 0) {
                    errors.push('Please enter a valid quantity');
                }
                break;
        }

        return errors;
    }

    isValidEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }

    isValidPhone(phone) {
        const normalized = phone.replace(/[\s\-\(\)]/g, '');
        return /^(\+?256|0)?7\d{8}$/.test(normalized) || /^(\+?256\d{9})$/.test(normalized);
    }

    displayFieldError(field, errors) {
        const formGroup = field.closest('.form-group');
        const existingError = formGroup.querySelector('.form-error');

        if (existingError) {
            existingError.remove();
        }

        if (errors.length > 0) {
            formGroup.classList.add('has-error');
            const errorElement = document.createElement('div');
            errorElement.className = 'form-error';
            errorElement.textContent = errors[0];
            formGroup.appendChild(errorElement);
        } else {
            formGroup.classList.remove('has-error');
        }
    }

    formatFieldName(name) {
        return name
            .replace(/_/g, ' ')
            .replace(/([A-Z])/g, ' $1')
            .toLowerCase()
            .split(' ')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }

    handleSubmit(e) {
        const fields = this.form.querySelectorAll('input, select, textarea');
        let isValid = true;

        fields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });

        if (!isValid) {
            e.preventDefault();
            this.scrollToFirstError();
        }

        return isValid;
    }

    scrollToFirstError() {
        const firstError = this.form.querySelector('.has-error');
        if (firstError) {
            firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
            firstError.querySelector('input, select, textarea').focus();
        }
    }
}

/* ===================================
   ALERT MESSAGE HANDLER
   =================================== */

class AlertManager {
    static show(message, type = 'info', duration = 5000) {
        const alertHTML = `
            <div class="alert alert-${type}">
                <div class="alert-icon">
                    ${this.getIcon(type)}
                </div>
                <div class="alert-content">
                    <div class="alert-title">${this.getTitle(type)}</div>
                    <div>${message}</div>
                </div>
            </div>
        `;

        const container = document.querySelector('.alert-container') || document.body;
        const alertElement = document.createElement('div');
        alertElement.innerHTML = alertHTML;
        container.insertBefore(alertElement.firstElementChild, container.firstChild);

        if (duration > 0) {
            setTimeout(() => {
                const alert = container.querySelector('.alert');
                if (alert) {
                    alert.remove();
                }
            }, duration);
        }
    }

    static success(message) {
        this.show(message, 'success', 5000);
    }

    static error(message) {
        this.show(message, 'danger', 5000);
    }

    static warning(message) {
        this.show(message, 'warning', 5000);
    }

    static info(message) {
        this.show(message, 'info', 5000);
    }

    static getIcon(type) {
        const icons = {
            success: '✓',
            danger: '✕',
            warning: '⚠',
            info: 'ℹ'
        };
        return icons[type] || 'ℹ';
    }

    static getTitle(type) {
        const titles = {
            success: 'Success',
            danger: 'Error',
            warning: 'Warning',
            info: 'Information'
        };
        return titles[type] || 'Message';
    }
}

/* ===================================
   CONFIRMATION DIALOG
   =================================== */

class ConfirmDialog {
    static show(message, onConfirm, onCancel) {
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';

        const dialog = document.createElement('div');
        dialog.className = 'modal-dialog';
        dialog.innerHTML = `
            <div class="modal-header">
                <h2>Confirm Action</h2>
                <button class="modal-close" type="button">&times;</button>
            </div>
            <div class="modal-body">
                <p>${message}</p>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary cancel-btn" type="button">Cancel</button>
                <button class="btn btn-danger confirm-btn" type="button">Confirm</button>
            </div>
        `;

        overlay.appendChild(dialog);
        document.body.appendChild(overlay);

        const confirmBtn = dialog.querySelector('.confirm-btn');
        const cancelBtn = dialog.querySelector('.cancel-btn');
        const closeBtn = dialog.querySelector('.modal-close');

        confirmBtn.addEventListener('click', () => {
            this.close(overlay);
            if (onConfirm) onConfirm();
        });

        cancelBtn.addEventListener('click', () => {
            this.close(overlay);
            if (onCancel) onCancel();
        });

        closeBtn.addEventListener('click', () => {
            this.close(overlay);
            if (onCancel) onCancel();
        });

        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                this.close(overlay);
                if (onCancel) onCancel();
            }
        });
    }

    static close(overlay) {
        overlay.remove();
    }
}

/* ===================================
   TABLE UTILITIES
   =================================== */

class TableManager {
    static enableRowSelection(tableSelector) {
        const table = document.querySelector(tableSelector);
        if (!table) return;

        const checkboxes = table.querySelectorAll('input[type="checkbox"]');
        const selectAllCheckbox = table.querySelector('thead input[type="checkbox"]');

        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener('change', (e) => {
                checkboxes.forEach(cb => cb.checked = e.target.checked);
                this.updateRowHighlight(table);
            });
        }

        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.updateRowHighlight(table);
            });
        });
    }

    static updateRowHighlight(table) {
        table.querySelectorAll('tbody tr').forEach(row => {
            const checkbox = row.querySelector('input[type="checkbox"]');
            if (checkbox && checkbox.checked) {
                row.style.backgroundColor = 'rgba(59, 130, 246, 0.05)';
            } else {
                row.style.backgroundColor = '';
            }
        });
    }

    static getSelectedRows(tableSelector) {
        const table = document.querySelector(tableSelector);
        const checkboxes = table.querySelectorAll('tbody input[type="checkbox"]:checked');
        return Array.from(checkboxes).map(cb => cb.closest('tr'));
    }

    static exportToCSV(tableSelector, filename = 'export.csv') {
        const table = document.querySelector(tableSelector);
        let csv = [];

        // Header
        const headers = [];
        table.querySelectorAll('thead th').forEach(th => {
            headers.push(this.escapeCSV(th.textContent));
        });
        csv.push(headers.join(','));

        // Rows
        table.querySelectorAll('tbody tr').forEach(tr => {
            const row = [];
            tr.querySelectorAll('td').forEach(td => {
                row.push(this.escapeCSV(td.textContent));
            });
            csv.push(row.join(','));
        });

        const csvContent = 'data:text/csv;charset=utf-8,' + csv.join('\n');
        const link = document.createElement('a');
        link.setAttribute('href', encodeURI(csvContent));
        link.setAttribute('download', filename);
        link.click();
    }

    static escapeCSV(str) {
        if (typeof str !== 'string') return '';
        return '"' + str.replace(/"/g, '""') + '"';
    }
}

/* ===================================
   INITIALIZE ON PAGE LOAD
   =================================== */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize form validator for all forms
    document.querySelectorAll('form').forEach((form, index) => {
        if (!form.classList.contains('no-validation')) {
            new FormValidator(`form:nth-of-type(${index + 1})`);
        }
    });

    // Auto-dismiss alerts
    document.querySelectorAll('.alert').forEach(alert => {
        if (alert.dataset.autoDismiss !== 'false') {
            const duration = alert.dataset.duration || 5000;
            setTimeout(() => alert.remove(), duration);
        }
    });
});

/* ===================================
   UTILITY FUNCTIONS
   =================================== */

function formatCurrency(value) {
    return new Intl.NumberFormat('en-UG', {
        style: 'currency',
        currency: 'UGX',
        minimumFractionDigits: 0
    }).format(value);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-UG', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    }).format(date);
}

function formatPhoneNumber(phone) {
    const cleaned = phone.replace(/\D/g, '');
    if (cleaned.length === 10) {
        return `+256${cleaned.substring(1)} (${cleaned.substring(1, 4)}) ${cleaned.substring(4, 7)}-${cleaned.substring(7)}`;
    }
    return phone;
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        AlertManager.success('Copied to clipboard');
    }).catch(() => {
        AlertManager.error('Failed to copy to clipboard');
    });
}

function printElement(selector) {
    const element = document.querySelector(selector);
    if (!element) return;

    const printWindow = window.open('', '', 'height=600,width=800');
    printWindow.document.write('<html><head><title>Print</title>');
    printWindow.document.write('<link rel="stylesheet" href="' + window.location.origin + '/static/css/standardized.css">');
    printWindow.document.write('</head><body>');
    printWindow.document.write(element.innerHTML);
    printWindow.document.write('</body></html>');
    printWindow.document.close();
    
    setTimeout(() => {
        printWindow.print();
    }, 250);
}
