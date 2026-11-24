/**
 * Bidirectional appear/disappear scroll animations for About Us cards,
 * bottom "LUWA TECH" watermark, Why Partner section, and Blog Copy-Link sharing.
 */
(function () {
    "use strict";

    function initLuwaAboutAnimations() {
        var targets = document.querySelectorAll(
            ".luwa-about-watermark, .luwa-about-card, .luwa-why-reveal"
        );
        var isEditorMode =
            document.body.classList.contains("editor_enable") ||
            window.location.search.indexOf("enable_editor") !== -1;

        if (targets.length) {
            if (isEditorMode) {
                targets.forEach(function (el) {
                    el.classList.add("is-in-view");
                    el.classList.remove("is-below", "is-above");
                });
            } else {
                targets.forEach(function (el) {
                    var rect = el.getBoundingClientRect();
                    if (rect.top < window.innerHeight && rect.bottom > 0) {
                        el.classList.add("is-in-view");
                    } else if (rect.top >= window.innerHeight) {
                        el.classList.add("is-below");
                    } else {
                        el.classList.add("is-above");
                    }
                });

                if ("IntersectionObserver" in window) {
                    var observer = new IntersectionObserver(
                        function (entries) {
                            entries.forEach(function (entry) {
                                var el = entry.target;
                                if (entry.isIntersecting) {
                                    el.classList.add("is-in-view");
                                    el.classList.remove("is-below", "is-above");
                                } else {
                                    el.classList.remove("is-in-view");
                                    if (entry.boundingClientRect.top < 0) {
                                        el.classList.add("is-above");
                                        el.classList.remove("is-below");
                                    } else {
                                        el.classList.add("is-below");
                                        el.classList.remove("is-above");
                                    }
                                }
                            });
                        },
                        {
                            threshold: 0.12,
                            rootMargin: "-10px 0px -30px 0px",
                        }
                    );

                    targets.forEach(function (el) {
                        observer.observe(el);
                    });
                } else {
                    targets.forEach(function (el) {
                        el.classList.add("is-in-view");
                    });
                }
            }
        }

        // Social share copy-link handler on /blog posts
        var copyBtns = document.querySelectorAll(".luwa-share-copy-btn");
        copyBtns.forEach(function (btn) {
            btn.addEventListener("click", function (e) {
                e.preventDefault();
                var url = btn.getAttribute("data-share-url") || window.location.href;
                var label = btn.querySelector(".luwa-share-copy-label");
                function markCopied() {
                    btn.classList.add("is-copied");
                    if (label) {
                        label.textContent = "Link Copied!";
                    }
                    setTimeout(function () {
                        btn.classList.remove("is-copied");
                        if (label) {
                            label.textContent = "Copy Link";
                        }
                    }, 2200);
                }
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(url).then(markCopied).catch(markCopied);
                } else {
                    var inp = document.createElement("input");
                    inp.value = url;
                    document.body.appendChild(inp);
                    inp.select();
                    try {
                        document.execCommand("copy");
                    } catch (err) {}
                    document.body.removeChild(inp);
                    markCopied();
                }
            });
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initLuwaAboutAnimations);
    } else {
        initLuwaAboutAnimations();
    }
})();
