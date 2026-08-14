(function (window) {
    const baseUrl = "/api/admin/finance";

    function authHeaders() {
        return window.AppAuth.criarHeadersAuth(window.AppAuth.garantirToken());
    }

    function jsonHeaders() {
        return window.AppAuth.criarHeadersJsonAuth(window.AppAuth.garantirToken());
    }

    function query(params = {}) {
        const search = new URLSearchParams();
        Object.entries(params).forEach(([key, value]) => {
            if (value !== null && value !== undefined && String(value) !== "") {
                search.set(key, String(value));
            }
        });
        return search.toString();
    }

    async function download(url, fallbackName) {
        const response = await window.AppApi.fetchResposta(url, { headers: authHeaders() });
        const blob = await response.blob();
        const disposition = response.headers.get("content-disposition") || "";
        const match = disposition.match(/filename="?([^";]+)"?/i);
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = match?.[1] || fallbackName;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(link.href);
    }

    window.FinanceApi = {
        summary: (month) => window.AppApi.fetchJson(`${baseUrl}/summary?${query({ month })}`, { headers: authHeaders() }),
        list: (month, status) => window.AppApi.fetchJson(`${baseUrl}/transactions?${query({ month, status })}`, { headers: authHeaders() }),
        create: (payload) => window.AppApi.fetchJson(`${baseUrl}/transactions`, {
            method: "POST", headers: jsonHeaders(), body: JSON.stringify(payload)
        }),
        update: (id, payload) => window.AppApi.fetchJson(`${baseUrl}/transactions/${id}`, {
            method: "PUT", headers: jsonHeaders(), body: JSON.stringify(payload)
        }),
        cancel: (id, reason) => window.AppApi.fetchJson(`${baseUrl}/transactions/${id}/cancel`, {
            method: "POST", headers: jsonHeaders(), body: JSON.stringify({ reason })
        }),
        upload: (id, file) => {
            const data = new FormData();
            data.append("file", file);
            return window.AppApi.fetchJson(`${baseUrl}/transactions/${id}/attachments`, {
                method: "POST", headers: authHeaders(), body: data
            });
        },
        removeAttachment: (transactionId, attachmentId) => window.AppApi.fetchResposta(
            `${baseUrl}/transactions/${transactionId}/attachments/${attachmentId}`,
            { method: "DELETE", headers: authHeaders() }
        ),
        downloadAttachment: (attachment) => download(
            `${baseUrl}/attachments/${attachment.token}`,
            attachment.original_name || "comprovante"
        ),
        downloadReport: (month) => download(
            `${baseUrl}/report.pdf?${query({ month })}`,
            `prestacao-contas-${month}.pdf`
        )
    };
})(window);
