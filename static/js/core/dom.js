(function (window) {
    function el(id) {
        return document.getElementById(id);
    }

    window.AppDom = Object.assign(window.AppDom || {}, {
        el,
    });
})(window);
