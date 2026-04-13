(function (window) {
    function paraIso(dataObj) {
        const ano = dataObj.getFullYear();
        const mes = String(dataObj.getMonth() + 1).padStart(2, "0");
        const dia = String(dataObj.getDate()).padStart(2, "0");
        return `${ano}-${mes}-${dia}`;
    }

    function hojeIso() {
        return paraIso(new Date());
    }

    function paraDataBr(dataIso) {
        const partes = String(dataIso || "").split("-");
        if (partes.length !== 3) {
            return String(dataIso || "");
        }
        return `${partes[2]}/${partes[1]}/${partes[0]}`;
    }

    function escaparHtml(valor) {
        return String(valor || "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll("\"", "&quot;")
            .replaceAll("'", "&#39;");
    }

    window.AppFormat = Object.assign(window.AppFormat || {}, {
        paraIso,
        hojeIso,
        paraDataBr,
        escaparHtml,
    });
})(window);
