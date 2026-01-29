/* exported onScanFailure, onScanStop */

/**
 * Handling successfull scanning result
 * @param {String} decodedText
 * @param {Object} decodedResult
 */
function onScanSuccess(decodedText, decodedResult) {
    // handle the scanned code as you like, for example:
    checkAndRetrieveIsbn(decodedText);
}

function onScanFailure(error) {
    // handle scan failure, usually better to ignore and keep scanning.
    // for example:
    // console.warn(`Code scan error = ${error}`);
}

const html5QrCode = new Html5Qrcode("reader");

function onScanStart() {
    const formatsToSupport = [
        Html5QrcodeSupportedFormats.EAN_13,
        Html5QrcodeSupportedFormats.EAN_8,
        Html5QrcodeSupportedFormats.UPC_EAN_EXTENSION
    ];

    const scanOptions = {
        fps: 10,
        qrbox: 150,
        aspectRatio: 0.5, //($(window).height() > $(window).width()) ? 2 : 0.5,
        formatsToSupport: formatsToSupport
    };

    $("button.start").hide();
    $("button.stop").show();
    $("#reader").show();

    html5QrCode.start({ facingMode: "environment" }, scanOptions, onScanSuccess);

    registerBeep();
}

function onScanStop() {
    $("button.start").show();
    $("button.stop").hide();
    $("#reader").hide();

    html5QrCode.stop();
}

onScanStart();
