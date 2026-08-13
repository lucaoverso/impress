(function (window) {
    const Blog = window.BlogAdmin;
    const allowedTags = new Set([
        "P", "BR", "STRONG", "B", "EM", "I", "U", "UL", "OL", "LI", "H2",
        "FIGURE", "IMG", "FIGCAPTION",
    ]);
    const allowedImageWidths = new Set(["25", "50", "75", "100"]);

    function sanitizeStyle(value) {
        const match = String(value || "").match(/text-align\s*:\s*(left|center|right)/i);
        return match ? `text-align: ${match[1].toLowerCase()}` : "";
    }

    function cleanNode(node, destination) {
        if (node.nodeType === Node.TEXT_NODE) {
            destination.appendChild(document.createTextNode(node.textContent || ""));
            return;
        }
        if (node.nodeType !== Node.ELEMENT_NODE) return;
        const tag = allowedTags.has(node.tagName) ? node.tagName.toLowerCase() : null;
        const target = tag ? document.createElement(tag) : destination;
        if (tag) {
            const style = sanitizeStyle(node.getAttribute("style"));
            if (style && ["p", "h2", "li"].includes(tag)) target.setAttribute("style", style);
            if (["figure", "img"].includes(tag) && node.dataset.blogImage) {
                target.dataset.blogImage = node.dataset.blogImage;
            }
            if (tag === "figure" && allowedImageWidths.has(node.dataset.width)) {
                target.dataset.width = node.dataset.width;
            }
            if (tag === "img") target.alt = node.getAttribute("alt") || "";
            destination.appendChild(target);
        }
        Array.from(node.childNodes).forEach((child) => cleanNode(child, target));
    }

    function sanitizeHtml(html) {
        const parsed = new DOMParser().parseFromString(`<div>${html || ""}</div>`, "text/html");
        const output = document.createElement("div");
        Array.from(parsed.body.firstElementChild?.childNodes || []).forEach((node) => {
            cleanNode(node, output);
        });
        return output.innerHTML;
    }

    function editor() {
        return Blog.el("blogRichEditor");
    }

    function notifyChange() {
        editor().dispatchEvent(new Event("input", { bubbles: true }));
    }

    function currentInsertionRange() {
        const selection = window.getSelection();
        if (!selection?.rangeCount) return null;
        const range = selection.getRangeAt(0);
        return editor().contains(range.commonAncestorContainer) ? range.cloneRange() : null;
    }

    function clipboardImage(clipboardData) {
        return Array.from(clipboardData?.items || [])
            .filter((item) => item.kind === "file" && item.type.startsWith("image/"))
            .map((item) => item.getAsFile())
            .find(Boolean) || null;
    }

    function execute(command, value = null) {
        editor().focus();
        document.execCommand("styleWithCSS", false, false);
        document.execCommand(command, false, value);
        notifyChange();
    }

    function selectedFigure() {
        return editor().querySelector("figure.is-selected[data-blog-image]");
    }

    function updateImageSizeControls(figure = selectedFigure()) {
        const controls = Blog.el("blogImageSizeControls");
        if (!controls) return;
        controls.hidden = !figure;
        const currentWidth = figure?.dataset.width || "100";
        controls.querySelectorAll("[data-blog-image-width]").forEach((button) => {
            const active = button.dataset.blogImageWidth === currentWidth;
            button.classList.toggle("is-active", active);
            button.setAttribute("aria-pressed", String(active));
        });
    }

    function setSelectedImageWidth(width) {
        const figure = selectedFigure();
        const normalized = String(width || "");
        if (!figure || !allowedImageWidths.has(normalized)) return;
        figure.dataset.width = normalized;
        updateImageSizeControls(figure);
        notifyChange();
    }

    function setup() {
        const toolbar = Blog.el("blogEditorToolbar");
        toolbar.addEventListener("mousedown", (event) => event.preventDefault());
        toolbar.addEventListener("click", (event) => {
            const button = event.target.closest("button");
            if (!button) return;
            if (button.dataset.blogCommand) execute(button.dataset.blogCommand);
            if (button.dataset.blogBlock) execute("formatBlock", button.dataset.blogBlock);
            if (button.dataset.blogImageWidth) {
                setSelectedImageWidth(button.dataset.blogImageWidth);
            }
        });

        editor().addEventListener("paste", (event) => {
            const imageFile = clipboardImage(event.clipboardData);
            if (imageFile) {
                event.preventDefault();
                void Blog.Images.uploadPastedImage(imageFile, currentInsertionRange());
                return;
            }
            const html = event.clipboardData?.getData("text/html");
            if (!html) return;
            event.preventDefault();
            document.execCommand("insertHTML", false, sanitizeHtml(html));
        });
        editor().addEventListener("click", (event) => {
            editor().querySelectorAll("figure.is-selected").forEach((item) => {
                item.classList.remove("is-selected");
            });
            const figure = event.target.closest("figure[data-blog-image]");
            if (figure) figure.classList.add("is-selected");
            updateImageSizeControls(figure);
        });
    }

    function setContent(html) {
        editor().innerHTML = sanitizeHtml(html);
        updateImageSizeControls(null);
    }

    function getContent() {
        return sanitizeHtml(editor().innerHTML).trim();
    }

    function findFigures(token) {
        return Array.from(editor().querySelectorAll("figure[data-blog-image]")).filter(
            (figure) => figure.dataset.blogImage === String(token)
        );
    }

    function syncImage(image, objectUrl = "") {
        findFigures(image.token).forEach((figure) => {
            const img = figure.querySelector("img");
            const caption = figure.querySelector("figcaption");
            if (img) {
                img.alt = image.alt_text || "";
                if (objectUrl) img.src = objectUrl;
            }
            if (caption) {
                caption.textContent = image.caption || "";
                caption.hidden = !image.caption;
            }
        });
    }

    function insertImage(image, objectUrl, insertionRange = null) {
        const figure = document.createElement("figure");
        figure.dataset.blogImage = image.token;
        figure.dataset.width = "50";
        figure.contentEditable = "false";
        const img = document.createElement("img");
        img.dataset.blogImage = image.token;
        img.src = objectUrl;
        img.alt = image.alt_text || "";
        const caption = document.createElement("figcaption");
        caption.textContent = image.caption || "";
        caption.hidden = !image.caption;
        figure.append(img, caption);

        const selection = window.getSelection();
        const selectedRange = insertionRange || currentInsertionRange();
        if (selectedRange && editor().contains(selectedRange.commonAncestorContainer)) {
            const range = selectedRange;
            range.deleteContents();
            range.insertNode(figure);
        } else {
            editor().appendChild(figure);
        }
        const paragraph = document.createElement("p");
        paragraph.appendChild(document.createElement("br"));
        figure.after(paragraph);
        if (selection) {
            const nextRange = document.createRange();
            nextRange.selectNodeContents(paragraph);
            nextRange.collapse(true);
            selection.removeAllRanges();
            selection.addRange(nextRange);
        }
        notifyChange();
        editor().querySelectorAll("figure.is-selected").forEach((item) => {
            item.classList.remove("is-selected");
        });
        figure.classList.add("is-selected");
        updateImageSizeControls(figure);
        paragraph.scrollIntoView({ behavior: "smooth", block: "center" });
    }

    function removeImage(token) {
        findFigures(token).forEach((figure) => figure.remove());
        updateImageSizeControls(null);
        notifyChange();
    }

    window.BlogAdmin.Editor = {
        setup,
        setContent,
        getContent,
        syncImage,
        insertImage,
        removeImage,
        findFigures,
    };
})(window);
