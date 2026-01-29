/* exported showToast */

/**
 * Keep reference to the toast template
 */
const toastTemplate = $("#iqoqo_toast");

/**
 * Shows given message in the bootstrap toast
 * @param {str} message
 */
function showToast(message) {
    toastTemplate.find(".toast-body").text(message);

    const toast = new bootstrap.Toast(toastTemplate);
    toast.show();
}
