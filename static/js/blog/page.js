(function (window) {
    const Blog = window.BlogAdmin;

    function filteredPosts() {
        const query = Blog.el("blogSearch").value.trim().toLocaleLowerCase("pt-BR");
        const status = Blog.el("blogStatusFilter").value;
        return Blog.state.posts.filter((post) => {
            const matchesText = !query || String(post.title || "").toLocaleLowerCase("pt-BR").includes(query);
            return matchesText && (!status || post.status === status);
        });
    }

    function renderPostList() {
        const list = Blog.el("blogPostList");
        const posts = filteredPosts();
        list.replaceChildren();
        Blog.el("blogPostCount").textContent = `${posts.length} artigo${posts.length === 1 ? "" : "s"}`;
        if (!posts.length) {
            const empty = document.createElement("div");
            empty.className = "blog-list-empty";
            const icon = document.createElement("i");
            icon.className = "bi bi-journal-x";
            icon.setAttribute("aria-hidden", "true");
            const text = document.createElement("p");
            text.textContent = Blog.state.posts.length
                ? "Nenhum artigo corresponde aos filtros."
                : "Nenhum artigo criado ainda.";
            empty.append(icon, text);
            list.appendChild(empty);
            return;
        }
        posts.forEach((post) => {
            const item = document.createElement("button");
            item.type = "button";
            item.className = "blog-post-item";
            item.classList.toggle("is-active", post.id === Blog.state.currentPost?.id);
            item.setAttribute("aria-current", post.id === Blog.state.currentPost?.id ? "true" : "false");
            const title = document.createElement("strong");
            title.textContent = post.title;
            const status = document.createElement("span");
            status.textContent = Blog.statusInfo(post.status).label;
            const date = document.createElement("small");
            date.textContent = `Atualizado em ${Blog.formatDate(post.updated_at)}`;
            item.append(title, status, date);
            item.addEventListener("click", () => void selectPost(post.id));
            list.appendChild(item);
        });
    }

    function canLeaveCurrent() {
        return !Blog.state.dirty || window.confirm("Descartar as alterações ainda não salvas?");
    }

    function updateCounters() {
        Blog.el("blogTitleCount").textContent = Blog.el("blogPostTitle").value.length;
        Blog.el("blogSummaryCount").textContent = Blog.el("blogPostSummary").value.length;
    }

    function setFormLocked(locked) {
        Blog.el("blogPostTitle").disabled = locked;
        Blog.el("blogPostSummary").disabled = locked;
        Blog.el("blogRichEditor").contentEditable = locked ? "false" : "true";
        Blog.el("blogEditorToolbar").querySelectorAll("button").forEach((button) => {
            button.disabled = locked;
        });
    }

    function updateEditorHeader() {
        const post = Blog.state.currentPost;
        const status = Blog.statusInfo(post?.status);
        const badge = Blog.el("blogEditorStatus");
        badge.textContent = status.label;
        badge.className = `blog-status ${status.className}`;
        Blog.el("blogEditorMeta").textContent = post?.id
            ? `Atualizado em ${Blog.formatDate(post.updated_at)}`
            : "Novo artigo ainda não salvo";
        const isDraft = post?.status === "DRAFT";
        const isPublished = post?.status === "PUBLISHED";
        const isArchived = post?.status === "ARCHIVED";
        Blog.el("blogPublishPost").hidden = !post?.id || !isDraft;
        Blog.el("blogUnpublishPost").hidden = !isPublished;
        Blog.el("blogArchivePost").hidden = !post?.id || isArchived;
        Blog.el("blogRestorePost").hidden = !isArchived;
        Blog.el("blogSavePost").hidden = isArchived;
        setFormLocked(isArchived);
    }

    function showPost(post) {
        Blog.Images.releaseUrls();
        Blog.state.currentPost = { ...post, images: Array.isArray(post.images) ? post.images : [] };
        Blog.el("blogEditorEmpty").hidden = true;
        Blog.el("blogEditorPanel").hidden = false;
        Blog.el("blogPostTitle").value = post.title || "";
        Blog.el("blogPostSummary").value = post.summary || "";
        Blog.Editor.setContent(post.body_html || "");
        updateCounters();
        updateEditorHeader();
        Blog.Images.render();
        Blog.markDirty(false);
        renderPostList();
    }

    function newPost() {
        if (!canLeaveCurrent()) return;
        showPost({
            id: null,
            title: "",
            summary: "",
            body_html: "",
            status: "DRAFT",
            updated_at: null,
            images: [],
        });
        Blog.setMessage("");
        Blog.el("blogPostTitle").focus();
    }

    async function selectPost(postId, force = false) {
        if (!force && postId === Blog.state.currentPost?.id) return;
        if (!force && !canLeaveCurrent()) return;
        Blog.setMessage("");
        try {
            showPost(await Blog.Api.getPost(postId));
        } catch (error) {
            Blog.setMessage(error.message || "Não foi possível carregar o artigo.", "error");
        }
    }

    function currentPayload() {
        return {
            id: Blog.state.currentPost?.id || null,
            title: Blog.el("blogPostTitle").value.trim(),
            summary: Blog.el("blogPostSummary").value.trim(),
            body_html: Blog.Editor.getContent(),
        };
    }

    async function saveCurrent({ silent = false } = {}) {
        const form = Blog.el("blogPostForm");
        if (!form.reportValidity()) return null;
        Blog.setBusy(true, "Salvando...");
        try {
            const images = Blog.state.currentPost?.images || [];
            const saved = await Blog.Api.savePost(currentPayload());
            showPost({ ...saved, images });
            await refreshPosts({ preserveEditor: true });
            if (!silent) Blog.setMessage("Artigo salvo com segurança.", "success");
            return saved;
        } catch (error) {
            Blog.setMessage(error.message || "Não foi possível salvar o artigo.", "error");
            return null;
        } finally {
            Blog.setBusy(false);
        }
    }

    async function refreshPosts({ preserveEditor = false } = {}) {
        try {
            Blog.state.posts = await Blog.Api.listPosts();
            renderPostList();
            if (!preserveEditor && !Blog.state.currentPost && Blog.state.posts.length) {
                await selectPost(Blog.state.posts[0].id, true);
            }
        } catch (error) {
            Blog.setMessage(error.message || "Não foi possível listar os artigos.", "error");
        }
    }

    async function changeStatus(action, successMessage) {
        let post = Blog.state.currentPost;
        if (!post?.id) return;
        if (action === "publish" && Blog.state.dirty) {
            const saved = await saveCurrent({ silent: true });
            if (!saved) return;
            post = Blog.state.currentPost;
        }
        try {
            const updated = await Blog.Api.changeStatus(post.id, action);
            showPost({ ...updated, images: post.images || [] });
            await refreshPosts({ preserveEditor: true });
            Blog.setMessage(successMessage, "success");
        } catch (error) {
            Blog.setMessage(error.message || "Não foi possível atualizar a situação do artigo.", "error");
        }
    }

    async function archiveCurrent() {
        if (!window.confirm("Arquivar este artigo? Ele deixará de aparecer no Blog público.")) return;
        await changeStatus("archive", "Artigo arquivado. Você poderá restaurá-lo quando precisar.");
    }

    function bindEvents() {
        Blog.el("blogNewPost").addEventListener("click", newPost);
        Blog.el("blogEmptyNewPost").addEventListener("click", newPost);
        Blog.el("blogSavePost").addEventListener("click", () => void saveCurrent());
        Blog.el("blogPublishPost").addEventListener("click", () => {
            void changeStatus("publish", "Artigo publicado.");
        });
        Blog.el("blogUnpublishPost").addEventListener("click", () => {
            void changeStatus("unpublish", "Artigo retirado do ar e mantido como rascunho.");
        });
        Blog.el("blogRestorePost").addEventListener("click", () => {
            void changeStatus("restore", "Artigo restaurado como rascunho.");
        });
        Blog.el("blogArchivePost").addEventListener("click", () => void archiveCurrent());
        Blog.el("blogRefresh").addEventListener("click", () => {
            if (canLeaveCurrent()) void refreshPosts();
        });
        ["blogSearch", "blogStatusFilter"].forEach((id) => {
            Blog.el(id).addEventListener("input", renderPostList);
        });
        ["blogPostTitle", "blogPostSummary"].forEach((id) => {
            Blog.el(id).addEventListener("input", () => {
                updateCounters();
                Blog.markDirty(true);
            });
        });
        Blog.el("blogRichEditor").addEventListener("input", () => Blog.markDirty(true));
        window.addEventListener("beforeunload", (event) => {
            if (!Blog.state.dirty) return;
            event.preventDefault();
            event.returnValue = "";
        });
    }

    async function initialize() {
        try {
            const user = await window.AppAuth.carregarUsuarioAtual({ forcar: true });
            if (window.AppAuth.normalizarCargoUsuario(user) !== "ADMIN") {
                window.location.href = "/servicos";
                return;
            }
            Blog.Editor.setup();
            Blog.Images.setup();
            bindEvents();
            await refreshPosts();
        } catch (error) {
            Blog.setMessage(error.message || "Não foi possível abrir a administração do Blog.", "error");
        }
    }

    initialize();
})(window);
