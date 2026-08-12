(() => {
    "use strict";

    const dialog = document.querySelector("[data-blog-lightbox]");
    const seenImages = new Set();
    const imageElements = Array.from(document.querySelectorAll(
        ".blog-article__cover img, [data-blog-article-body] figure img"
    )).filter((element) => {
        const key = element.dataset.blogImage || element.currentSrc || element.src;
        if (seenImages.has(key)) return false;
        seenImages.add(key);
        return true;
    });
    if (!dialog || !imageElements.length || typeof dialog.showModal !== "function") return;

    const displayImage = dialog.querySelector("[data-blog-lightbox-image]");
    const caption = dialog.querySelector("[data-blog-lightbox-caption]");
    const count = dialog.querySelector("[data-blog-lightbox-count]");
    const previous = dialog.querySelector("[data-blog-lightbox-prev]");
    const next = dialog.querySelector("[data-blog-lightbox-next]");
    const close = dialog.querySelector("[data-blog-lightbox-close]");
    let currentIndex = 0;
    let trigger = null;
    let touchStartX = null;

    const items = imageElements.map((element) => {
        const figure = element.closest("figure");
        return {
            src: element.currentSrc || element.src,
            alt: element.alt || "Imagem do artigo",
            caption: figure?.querySelector("figcaption")?.textContent?.trim() || "",
            element,
        };
    });

    function render(index) {
        currentIndex = (index + items.length) % items.length;
        const item = items[currentIndex];
        displayImage.src = item.src;
        displayImage.alt = item.alt;
        caption.textContent = item.caption;
        caption.hidden = !item.caption;
        count.textContent = `Imagem ${currentIndex + 1} de ${items.length}`;
        previous.hidden = items.length < 2;
        next.hidden = items.length < 2;
    }

    function open(index, source) {
        trigger = source;
        render(index);
        dialog.showModal();
        close.focus();
    }

    imageElements.forEach((element, index) => {
        element.tabIndex = 0;
        element.setAttribute("role", "button");
        element.setAttribute("aria-label", `Ampliar imagem: ${items[index].alt}`);
        element.addEventListener("click", () => open(index, element));
        element.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                open(index, element);
            }
        });
    });

    previous.addEventListener("click", () => render(currentIndex - 1));
    next.addEventListener("click", () => render(currentIndex + 1));
    close.addEventListener("click", () => dialog.close());
    dialog.addEventListener("click", (event) => {
        if (event.target === dialog) dialog.close();
    });
    dialog.addEventListener("close", () => {
        displayImage.removeAttribute("src");
        trigger?.focus();
    });
    dialog.addEventListener("keydown", (event) => {
        if (event.key === "ArrowLeft") {
            event.preventDefault();
            render(currentIndex - 1);
        }
        if (event.key === "ArrowRight") {
            event.preventDefault();
            render(currentIndex + 1);
        }
    });
    dialog.addEventListener("touchstart", (event) => {
        touchStartX = event.changedTouches[0]?.clientX ?? null;
    }, { passive: true });
    dialog.addEventListener("touchend", (event) => {
        if (touchStartX === null || items.length < 2) return;
        const distance = (event.changedTouches[0]?.clientX ?? touchStartX) - touchStartX;
        if (Math.abs(distance) > 55) render(currentIndex + (distance < 0 ? 1 : -1));
        touchStartX = null;
    }, { passive: true });
})();
