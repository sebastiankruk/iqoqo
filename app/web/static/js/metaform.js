let checkingIsbn = false;
let lastIsbnCode = null;

/**
 * Determines which button is set as primary and which as secondary
 * @param {bool} addButton
 */
function setButtonPrimary(addButton) {
  const primaryButton = addButton ? 'add' : 'update';
  const secondaryButton = addButton ? 'update' : 'add';

  $(`button.${primaryButton}`).addClass('btn-primary').removeClass('btn-secondary');
  $(`button.${secondaryButton}`).removeClass('btn-primary').addClass('btn-secondary');
}

/**
 * Updates status with given ISBN number and (optional) title and authors from data
 * @param {String} isbn
 * @param {Map} data
 * @returns data
 */
function updateLabel(sisbn, data) {
  const isbn = sisbn.substr(sisbn.length - 1) === 'X' ? sisbn.substr(0, sisbn.length - 1) : sisbn;

  $('#lastISBN .isbn .meta-value input').val(isbn);
  $('#navigation-buttons').removeClass('noitem');
  $('#navigation-buttons').addClass('can-add');
  $('#navigation-buttons').addClass('can-update');

  if (data) {
    $('#lastISBN .title .meta-value input').val(data.Title);
    $('#lastISBN .authors .meta-value input').val(data.Authors.join(', '));

    console.log(`Found book with ISBN = ${isbn}`, data);
    $('#lastISBN').addClass('found').removeClass('notfound');
    playBeep('ding');
  } else {
    $('#lastISBN .title .meta-value input').val('');
    $('#lastISBN .authors .meta-value input').val('');

    console.warn(`Could not find book with ISBN = ${isbn}`);
    $('#lastISBN').addClass('notfound').removeClass('found');
    playBeep('error');
  }

  setButtonPrimary(true);

  $.get(`/api/item/${sisbn}`, function (item_ids) {
    console.log(`Book with ISBN = ${sisbn} already added`, item_ids);
    setButtonPrimary(false);
    checkingIsbn = false;
  }).fail(function (jqXHR, textStatus) {
    if (jqXHR.status == 404) {
      $('#navigation-buttons').addClass('noitem');
    }
    checkingIsbn = false;
  });

  return data;
}

/**
 * Checking and retrieving metadata on ISBN
 * @param {str} isbn
 */
/* exported checkAndRetrieveIsbn */
function checkAndRetrieveIsbn(isbn) {
  if (!checkingIsbn && isbn && isbn !== lastIsbnCode) {
    checkingIsbn = true;

    isbn = xfixIsbn10(isbn);

    $('#navigation-buttons').removeClass('can-update');

    if (isValidIsbn(isbn)) {
      $('#lastISBN .isbn .meta-value input').removeClass('is-invalid');
      retrieveIsbnData(isbn);
    } else {
      // handle all issues with incorrectly formatted ISBN
      lastIsbnCode = '';
      checkingIsbn = false;
      console.warn(`Given ISBN = ${isbn} was incorrect`);
      $('#lastISBN .isbn .meta-value input').val(isbn);
      $('#lastISBN .isbn .meta-value input').addClass('is-invalid');
      $('#navigation-buttons').removeClass('can-add');
    }
  }
}

/**
 * Attempts to retrieve metadata based on the given ISBN
 * @param {string} isbn
 */
function retrieveIsbnData(isbn) {
  lastIsbnCode = isbn;

  $.ajax({
    type: 'GET',
    url: `/api/isbn/${isbn}`,
    success: function (data) {
      // ISBN was correct and book was found
      return updateLabel(isbn, data);
    },
  }).fail(function (jqXHR, textStatus) {
    switch (jqXHR.status) {
      // ISBN was correct but book was not found
      case 404: {
        showToast(`Could not find book with ISBN = ${isbn}`);
        return updateLabel(isbn, null);
      }
      // ISBN was incorrect
      case 400: {
        showToast(`Given ISBN = ${isbn} was incorrect`);
        lastIsbnCode = '';
        checkingIsbn = false;
        $('#navigation-buttons').removeClass('can-add');
      }
    }
  });
}

/**
 * In case we have only 9 digits in ISBN10 we will add X at the end
 * @param {str} isbn
 * @returns
 */
function xfixIsbn10(isbn) {
  return isbn.length == 9 ? isbn + 'X' : isbn;
}

/**
 * Will clear all meta fields
 */
function onMetaClear() {
  $('.meta-value input').val('');
  onMetaUpdate();
}

/**
 * Will check which buttons to e
 */
function onMetaUpdate() {
  const empty = $('.meta-value input').val() === '';
  $('button.clear').toggleClass('can-clear', !empty);

  const isbnEmpty = $('.isbn .meta-value input').val() === '';
  $('button.check').toggleClass('can-check', !isbnEmpty);

  if (empty) {
    $('#navigation-buttons').removeClass('can-add');
    $('#navigation-buttons').removeClass('can-update');
  }
}

$('button.clear').on('click', onMetaClear);

$('.meta-value input').on('keyup', onMetaUpdate);
