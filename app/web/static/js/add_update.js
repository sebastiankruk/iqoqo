/**
 * Will check given ISBN and fill in title/authors if found
 */
function onISBNCheck() {
    const isbn = $("#lastISBN .isbn .meta-value input").val();
    console.log(isbn);
    checkAndRetrieveIsbn(isbn);
}
$("button.check").on("click", onISBNCheck);

if (window.location.hash) {
    $("#lastISBN .isbn .meta-value input").val(window.location.hash.substring(1));
    onISBNCheck();
}
