/**
 * Helper function that either adds an item or simply updates manifestation
 * @param {bool} isAdd
 */
function _onBookPost(isAdd) {
    let isbn = $("#lastISBN .isbn .meta-value input").val();
    isbn = xfixIsbn10(isbn);

    const metadata =
    $("#lastISBN").hasClass("notfound") || !isAdd
        ? {
            Title: $("#lastISBN .title .meta-value input").val(),
            Authors: $("#lastISBN .authors .meta-value input")
                .val()
                .split(",")
                .map(t => t.trim())
        }
        : {};
    const action = isAdd ? "item" : "isbn";
    $.ajax({
        url: `${action}/${isbn}`,
        contentType: "application/json",
        data: JSON.stringify(metadata),
        type: "POST",
        async: false,
        dataType: "json"
    }).done(function (data) {
        $("#navigation-buttons").removeClass("noitem");
        setButtonPrimary(false);
        const message = isAdd ? `Successfully added ${isbn} item` : `Successfully updated ${isbn} manifestation`;
        showToast(message);
        console.log(message, data);
    });
}

/**
 * Adding a book manifestation as an item.
 * If title or authors are set - manifest can be updated before making an item
 */
function onBookAdd() {
    _onBookPost(true);
}

/**
 * Call to send an update to book meta
 */
function onBookUpdate() {
    _onBookPost(false);
}

$("button.add").on("click", onBookAdd);
$("button.update").on("click", onBookUpdate);
