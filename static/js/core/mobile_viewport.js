(function configureIosViewport() {
    const isIosDevice = /iPad|iPhone|iPod/.test(navigator.userAgent)
        || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
    if (!isIosDevice) return;

    const viewport = document.querySelector('meta[name="viewport"]');
    if (!viewport) return;

    const directives = new Map(
        viewport.content
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean)
            .map((item) => {
                const [name, ...value] = item.split("=");
                return [name.trim(), value.join("=").trim()];
            }),
    );

    directives.set("width", "device-width");
    directives.set("initial-scale", "1");
    directives.set("maximum-scale", "1");
    directives.set("viewport-fit", "cover");
    viewport.content = Array.from(directives, ([name, value]) => (
        value ? `${name}=${value}` : name
    )).join(", ");
})();
