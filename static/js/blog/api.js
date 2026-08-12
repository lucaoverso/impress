(function (window) {
    const { criarHeadersAuth, criarHeadersJsonAuth, garantirToken } = window.AppAuth;
    const { fetchComAuth, fetchJson, obterMensagemErroResposta } = window.AppApi;
    const token = garantirToken();
    const authHeaders = criarHeadersAuth(token);
    const jsonHeaders = criarHeadersJsonAuth(token);
    const baseUrl = "/api/admin/blog";

    function listPosts() {
        return fetchJson(`${baseUrl}/posts?limit=100`, { headers: authHeaders });
    }

    function getPost(postId) {
        return fetchJson(`${baseUrl}/posts/${postId}`, { headers: authHeaders });
    }

    function savePost(post) {
        const isNew = !post.id;
        return fetchJson(isNew ? `${baseUrl}/posts` : `${baseUrl}/posts/${post.id}`, {
            method: isNew ? "POST" : "PUT",
            headers: jsonHeaders,
            body: JSON.stringify({
                title: post.title,
                summary: post.summary,
                body_html: post.body_html,
            }),
        });
    }

    function changeStatus(postId, action) {
        return fetchJson(`${baseUrl}/posts/${postId}/${action}`, {
            method: "POST",
            headers: authHeaders,
        });
    }

    function uploadImage(postId, formData) {
        return fetchJson(`${baseUrl}/posts/${postId}/images`, {
            method: "POST",
            headers: authHeaders,
            body: formData,
        });
    }

    function updateImage(postId, imageId, payload) {
        return fetchJson(`${baseUrl}/posts/${postId}/images/${imageId}`, {
            method: "PATCH",
            headers: jsonHeaders,
            body: JSON.stringify(payload),
        });
    }

    function setCover(postId, imageId) {
        return fetchJson(`${baseUrl}/posts/${postId}/cover/${imageId}`, {
            method: "PUT",
            headers: authHeaders,
        });
    }

    function removeImage(postId, imageId) {
        return fetchJson(`${baseUrl}/posts/${postId}/images/${imageId}`, {
            method: "DELETE",
            headers: authHeaders,
        });
    }

    async function loadImage(tokenValue, thumbnail = false) {
        const suffix = thumbnail ? "?thumbnail=true" : "";
        const response = await fetchComAuth(
            `${baseUrl}/images/${encodeURIComponent(tokenValue)}${suffix}`,
            { headers: authHeaders }
        );
        if (!response.ok) {
            throw new Error(await obterMensagemErroResposta(response, "Imagem indisponível."));
        }
        return URL.createObjectURL(await response.blob());
    }

    window.BlogAdmin.Api = {
        listPosts,
        getPost,
        savePost,
        changeStatus,
        uploadImage,
        updateImage,
        setCover,
        removeImage,
        loadImage,
    };
})(window);
