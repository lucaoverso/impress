(function (window) {
    const state = {
        posts: [],
        currentPost: null,
        dirty: false,
        busy: false,
        imageUrls: new Map(),
    };

    const STATUS = {
        DRAFT: { label: "Rascunho", className: "is-draft" },
        PUBLISHED: { label: "Publicado", className: "is-published" },
        ARCHIVED: { label: "Arquivado", className: "is-archived" },
    };

    function el(id) {
        return document.getElementById(id);
    }

    function setMessage(text, kind = "") {
        const target = el("blogPageMessage");
        if (!target) return;
        const normalized = String(text || "").trim();
        target.textContent = /failed to fetch|networkerror/i.test(normalized)
            ? "Não foi possível conectar ao servidor. Verifique a conexão e tente novamente."
            : normalized;
        target.classList.toggle("is-error", kind === "error");
        target.classList.toggle("is-success", kind === "success");
    }

    function setBusy(busy, label = "Aguarde...") {
        state.busy = Boolean(busy);
        document.querySelectorAll("[data-blog-busy-action], #blogSavePost").forEach((button) => {
            button.disabled = state.busy;
        });
        const save = el("blogSavePost");
        if (!save) return;
        if (busy) {
            save.dataset.previousLabel = save.textContent.trim();
            save.textContent = label;
        } else if (save.dataset.previousLabel) {
            save.innerHTML = '<i class="bi bi-check2" aria-hidden="true"></i> Salvar alterações';
            delete save.dataset.previousLabel;
        }
    }

    function formatDate(value) {
        if (!value) return "Ainda não salvo";
        const normalized = String(value).replace(" ", "T") + "Z";
        const date = new Date(normalized);
        if (Number.isNaN(date.getTime())) return String(value);
        return new Intl.DateTimeFormat("pt-BR", {
            dateStyle: "short",
            timeStyle: "short",
        }).format(date);
    }

    function statusInfo(status) {
        return STATUS[status] || STATUS.DRAFT;
    }

    function markDirty(dirty = true) {
        state.dirty = Boolean(dirty);
        document.body.classList.toggle("blog-has-unsaved-changes", state.dirty);
    }

    window.BlogAdmin = Object.assign(window.BlogAdmin || {}, {
        state,
        el,
        setMessage,
        setBusy,
        formatDate,
        statusInfo,
        markDirty,
    });
})(window);
