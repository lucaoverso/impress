(function (window) {
    const Blog = window.BlogAdmin;

    function urlKey(token, thumbnail) {
        return `${token}:${thumbnail ? "thumb" : "main"}`;
    }

    async function getUrl(token, thumbnail = false) {
        const key = urlKey(token, thumbnail);
        if (Blog.state.imageUrls.has(key)) return Blog.state.imageUrls.get(key);
        const url = await Blog.Api.loadImage(token, thumbnail);
        Blog.state.imageUrls.set(key, url);
        return url;
    }

    function releaseUrls() {
        Blog.state.imageUrls.forEach((url) => URL.revokeObjectURL(url));
        Blog.state.imageUrls.clear();
    }

    function replaceImage(updated) {
        const post = Blog.state.currentPost;
        if (!post) return;
        post.images = (post.images || []).map((image) => (
            image.id === updated.id ? updated : image
        ));
    }

    function button(label, className = "", icon = "") {
        const element = document.createElement("button");
        element.type = "button";
        element.className = className;
        if (icon) {
            const symbol = document.createElement("i");
            symbol.className = `bi ${icon}`;
            symbol.setAttribute("aria-hidden", "true");
            element.append(symbol, document.createTextNode(` ${label}`));
        } else {
            element.textContent = label;
        }
        return element;
    }

    function field(labelText, value, maxLength) {
        const label = document.createElement("label");
        label.className = "blog-field";
        const text = document.createElement("span");
        text.textContent = labelText;
        const input = document.createElement("input");
        input.type = "text";
        input.maxLength = maxLength;
        input.value = value || "";
        label.append(text, input);
        return { label, input };
    }

    async function hydrateFigure(image) {
        if (!Blog.Editor.findFigures(image.token).length) return;
        try {
            Blog.Editor.syncImage(image, await getUrl(image.token));
        } catch (_error) {
            Blog.Editor.syncImage(image);
        }
    }

    function createImageItem(image) {
        const item = document.createElement("article");
        item.className = "blog-image-item";
        const preview = document.createElement("div");
        preview.className = "blog-image-preview";
        const img = document.createElement("img");
        img.alt = image.alt_text || "Prévia da imagem enviada";
        preview.appendChild(img);
        if (image.is_cover) {
            const cover = document.createElement("span");
            cover.className = "blog-cover-label";
            cover.textContent = "Imagem de capa";
            preview.appendChild(cover);
        }
        void getUrl(image.token, true).then((url) => { img.src = url; }).catch(() => {
            img.alt = "Imagem indisponível";
        });

        const content = document.createElement("div");
        const fields = document.createElement("div");
        fields.className = "blog-image-fields";
        const alt = field("Texto alternativo", image.alt_text, 180);
        const caption = field("Legenda (opcional)", image.caption, 500);
        fields.append(alt.label, caption.label);

        const actions = document.createElement("div");
        actions.className = "blog-image-actions";
        const save = button("Salvar dados", "", "bi-check2");
        const insert = button("Inserir no artigo", "", "bi-file-earmark-plus");
        actions.append(save, insert);
        if (!image.is_cover) {
            const setCover = button("Definir como capa", "", "bi-star");
            setCover.addEventListener("click", () => void setCoverImage(image));
            actions.appendChild(setCover);
        }
        const remove = button("Remover", "blog-remove-image", "bi-trash3");
        actions.appendChild(remove);
        content.append(fields, actions);
        item.append(preview, content);

        save.addEventListener("click", () => void saveMetadata(image, alt.input, caption.input));
        insert.addEventListener("click", () => void insertIntoArticle(image));
        remove.addEventListener("click", () => void removeStoredImage(image));
        return item;
    }

    function render() {
        const gallery = Blog.el("blogImageGallery");
        const post = Blog.state.currentPost;
        const images = Array.isArray(post?.images) ? post.images : [];
        gallery.replaceChildren();
        Blog.el("blogImageCount").textContent = `${images.length} de 20`;
        Blog.el("blogImageUpload").disabled = !post?.id || post.status === "ARCHIVED";
        Blog.el("blogUploadHint").hidden = Boolean(post?.id);
        Blog.el("blogImageCover").checked = images.length === 0;
        if (!images.length) {
            const empty = document.createElement("p");
            empty.className = "blog-gallery-empty";
            empty.textContent = post?.id
                ? "Nenhuma imagem enviada. Adicione a capa ou imagens para o texto."
                : "As imagens ficarão disponíveis depois do primeiro salvamento.";
            gallery.appendChild(empty);
            return;
        }
        images.forEach((image) => {
            gallery.appendChild(createImageItem(image));
            void hydrateFigure(image);
        });
    }

    async function saveMetadata(image, altInput, captionInput) {
        try {
            const updated = await Blog.Api.updateImage(image.post_id, image.id, {
                alt_text: altInput.value.trim(),
                caption: captionInput.value.trim(),
            });
            replaceImage(updated);
            Blog.Editor.syncImage(updated, await getUrl(updated.token));
            render();
            Blog.markDirty(true);
            Blog.setMessage("Dados da imagem atualizados. Salve o artigo para guardar alterações no texto.", "success");
        } catch (error) {
            Blog.setMessage(error.message || "Não foi possível atualizar a imagem.", "error");
        }
    }

    async function setCoverImage(image) {
        try {
            const updated = await Blog.Api.setCover(image.post_id, image.id);
            Blog.state.currentPost.images = Blog.state.currentPost.images.map((item) => ({
                ...item,
                is_cover: item.id === updated.id,
            }));
            render();
            Blog.setMessage("Imagem de capa definida.", "success");
        } catch (error) {
            Blog.setMessage(error.message || "Não foi possível definir a capa.", "error");
        }
    }

    async function insertIntoArticle(image) {
        try {
            Blog.Editor.insertImage(image, await getUrl(image.token));
            Blog.setMessage("Imagem inserida no conteúdo. Salve as alterações do artigo.", "success");
        } catch (error) {
            Blog.setMessage(error.message || "Não foi possível inserir a imagem.", "error");
        }
    }

    async function removeStoredImage(image) {
        if (!window.confirm("Remover esta imagem do artigo? Ela também sairá do conteúdo.")) return;
        try {
            await Blog.Api.removeImage(image.post_id, image.id);
            Blog.Editor.removeImage(image.token);
            Blog.state.currentPost.images = Blog.state.currentPost.images.filter(
                (item) => item.id !== image.id
            );
            [true, false].forEach((thumbnail) => {
                const key = urlKey(image.token, thumbnail);
                const url = Blog.state.imageUrls.get(key);
                if (url) URL.revokeObjectURL(url);
                Blog.state.imageUrls.delete(key);
            });
            render();
            Blog.setMessage("Imagem removida.", "success");
        } catch (error) {
            Blog.setMessage(error.message || "Não foi possível remover a imagem.", "error");
        }
    }

    async function upload() {
        const post = Blog.state.currentPost;
        const fileInput = Blog.el("blogImageFile");
        const file = fileInput.files?.[0];
        if (!post?.id || !file) {
            Blog.setMessage("Escolha uma imagem antes de enviar.", "error");
            fileInput.focus();
            return;
        }
        const form = new FormData();
        form.append("file", file);
        form.append("alt_text", Blog.el("blogImageAlt").value.trim());
        form.append("caption", Blog.el("blogImageCaption").value.trim());
        form.append("is_cover", String(Blog.el("blogImageCover").checked));
        const buttonElement = Blog.el("blogUploadImage");
        buttonElement.disabled = true;
        buttonElement.textContent = "Enviando...";
        try {
            const image = await Blog.Api.uploadImage(post.id, form);
            post.images.push(image);
            fileInput.value = "";
            Blog.el("blogImageAlt").value = "";
            Blog.el("blogImageCaption").value = "";
            render();
            Blog.setMessage("Imagem enviada. Agora você pode inseri-la no artigo.", "success");
        } catch (error) {
            Blog.setMessage(error.message || "Não foi possível enviar a imagem.", "error");
        } finally {
            buttonElement.disabled = false;
            buttonElement.innerHTML = '<i class="bi bi-upload" aria-hidden="true"></i> Enviar imagem';
        }
    }

    async function uploadInlineImage(file, insertionRange, source = "colada") {
        const post = Blog.state.currentPost;
        if (!post?.id) {
            Blog.setMessage("Salve o artigo antes de colar ou arrastar imagens no texto.", "error");
            return;
        }
        if (post.status === "ARCHIVED") {
            Blog.setMessage("Restaure o artigo antes de adicionar imagens.", "error");
            return;
        }

        const form = new FormData();
        form.append("file", file, file.name || `imagem-${source}.png`);
        form.append("alt_text", "");
        form.append("caption", "");
        form.append("is_cover", String((post.images || []).length === 0));
        const richEditor = Blog.el("blogRichEditor");
        richEditor.setAttribute("aria-busy", "true");
        Blog.setMessage(`Enviando a imagem ${source}...`);
        try {
            const image = await Blog.Api.uploadImage(post.id, form);
            post.images.push(image);
            render();
            Blog.Editor.insertImage(image, await getUrl(image.token), insertionRange);
            Blog.markDirty(true);
            Blog.setMessage(
                `Imagem ${source} e selecionada. Escolha 25%, 50%, 75% ou 100% na barra e preencha o texto alternativo.`,
                "success"
            );
        } catch (error) {
            Blog.setMessage(error.message || "Não foi possível inserir a imagem.", "error");
        } finally {
            richEditor.removeAttribute("aria-busy");
        }
    }

    function setup() {
        Blog.el("blogUploadImage").addEventListener("click", () => void upload());
        Blog.el("blogImageFile").addEventListener("change", (event) => {
            const name = event.target.files?.[0]?.name;
            const label = event.target.closest("label")?.querySelector("strong");
            if (label) label.textContent = name || "Escolher imagem";
        });
    }

    window.BlogAdmin.Images = { setup, render, releaseUrls, getUrl, uploadInlineImage };
})(window);
