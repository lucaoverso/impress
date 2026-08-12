(function (window) {
    const Blog = window.BlogAdmin;
    const allowedTags = new Set([
        "P", "BR", "STRONG", "B", "EM", "I", "U", "UL", "OL", "LI", "H2",
        "FIGURE", "IMG", "FIGCAPTION",
    ]);

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

    function execute(command, value = null) {
        editor().focus();
        document.execCommand("styleWithCSS", false, false);
        document.execCommand(command, false, value);
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
        });

        editor().addEventListener("paste", (event) => {
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
        });
    }

    function setContent(html) {
        editor().innerHTML = sanitizeHtml(html);
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

    function insertImage(image, objectUrl) {
        const figure = document.createElement("figure");
        figure.dataset.blogImage = image.token;
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
        if (selection?.rangeCount && editor().contains(selection.anchorNode)) {
            const range = selection.getRangeAt(0);
            range.deleteContents();
            range.insertNode(figure);
        } else {
            editor().appendChild(figure);
        }
        const paragraph = document.createElement("p");
        paragraph.appendChild(document.createElement("br"));
        figure.after(paragraph);
        notifyChange();
        paragraph.scrollIntoView({ behavior: "smooth", block: "center" });
    }

    function removeImage(token) {
        findFigures(token).forEach((figure) => figure.remove());
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
