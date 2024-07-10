setTimeout(function() {
    if (typeof (GLOBALS)=="undefined") return;
    /* Example: Send data from the page to your Chrome extension */
    document.dispatchEvent(new CustomEvent('RW759_connectExtension', {
        detail: GLOBALS // Some variable from Gmail.
    }));
}, 100);