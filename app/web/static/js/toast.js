/**
 * Keep reference to the toast template
 */
let toastTemplate = $('#iqoqo_toast');

/**
 * Shows given message in the bootstrap toast
 * @param {str} message
 */
function showToast(message) {
  toastTemplate.find('.toast-body').text(message);

  let toast = new bootstrap.Toast(toastTemplate);
  toast.show();
}
