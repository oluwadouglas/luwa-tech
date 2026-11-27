/**
 * Luwa Tech Interactive Website Features
 * 1. Social Share Bulletproof Copy-Link handler with clipboard API + fallback & toast
 * 2. Background WhatsApp Engine direct dispatch (no wa.me redirect / chat creation links)
 * 3. Bidirectional appear/disappear scroll animations for About cards & watermark
 */
(function () {
    "use strict";

    // Toast Notification helper
    function showLuwaToast(msg, type) {
        var container = document.getElementById("luwaToastContainer");
        if (!container) {
            container = document.createElement("div");
            container.id = "luwaToastContainer";
            container.className = "luwa-toast-container";
            document.body.appendChild(container);
        }
        var toast = document.createElement("div");
        toast.className = "luwa-toast " + (type || "success");
        var iconClass = (type === "error") ? "fa-exclamation-circle text-danger" : "fa-check-circle text-success";
        toast.innerHTML = '<i class="fas ' + iconClass + ' me-2"></i><span>' + msg + '</span>';
        container.appendChild(toast);
        setTimeout(function () {
            toast.style.opacity = "0";
            toast.style.transform = "translateY(12px)";
            toast.style.transition = "all 0.3s ease";
            setTimeout(function () {
                if (toast.parentNode) toast.parentNode.removeChild(toast);
            }, 300);
        }, 3200);
    }

    // 1. Social share Copy-Link handler
    function copyTextToClipboard(text, onSuccess, onError) {
        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(text).then(onSuccess).catch(function () {
                fallbackCopy(text, onSuccess, onError);
            });
        } else {
            fallbackCopy(text, onSuccess, onError);
        }
    }

    function fallbackCopy(text, onSuccess, onError) {
        var textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.position = "fixed";
        textArea.style.top = "-9999px";
        textArea.style.left = "-9999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        var successful = false;
        try {
            successful = document.execCommand("copy");
        } catch (err) {
            successful = false;
        }
        document.body.removeChild(textArea);
        if (successful) {
            if (onSuccess) onSuccess();
        } else {
            if (onError) onError();
        }
    }

    // Global click listener for copy buttons
    document.addEventListener("click", function (e) {
        var btn = e.target.closest(".luwa-share-copy-btn");
        if (!btn) return;
        e.preventDefault();
        e.stopPropagation();

        var rawUrl = btn.getAttribute("data-share-url") || window.location.href;
        var cleanUrl = rawUrl.split("#")[0];
        var label = btn.querySelector(".luwa-share-copy-label");
        var icon = btn.querySelector("i");

        copyTextToClipboard(
            cleanUrl,
            function () {
                btn.classList.add("is-copied");
                if (label) label.textContent = "Copied!";
                if (icon) icon.className = "fas fa-check me-1";
                showLuwaToast("Article link copied to clipboard!", "success");
                setTimeout(function () {
                    btn.classList.remove("is-copied");
                    if (label) label.textContent = "Copy Link";
                    if (icon) icon.className = "fas fa-link me-1";
                }, 2500);
            },
            function () {
                showLuwaToast("Failed to copy link automatically.", "error");
            }
        );
    });

    // 2. Global WhatsApp Background Engine Modal & Interceptor
    function ensureWhatsAppModal() {
        if (document.getElementById("luwaWhatsAppModal")) return;

        var backdrop = document.createElement("div");
        backdrop.id = "luwaWhatsAppModal";
        backdrop.className = "luwa-wa-modal-backdrop";
        backdrop.innerHTML = [
            '<div class="luwa-wa-modal-card" role="dialog" aria-modal="true" aria-labelledby="luwaWaTitle">',
            '  <div class="luwa-wa-modal-header">',
            '    <div class="d-flex align-items-center justify-content-between">',
            '      <h4 id="luwaWaTitle"><i class="fab fa-whatsapp" style="color:#25d366;font-size:24px;"></i> Luwa Tech WhatsApp Engine</h4>',
            '      <button type="button" class="luwa-wa-modal-close" id="luwaWaCloseBtn" aria-label="Close">&times;</button>',
            '    </div>',
            '    <div class="luwa-wa-status-badge">',
            '      <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#25d366;"></span> Live Desk Connected (+256 787 819 453)',
            '    </div>',
            '  </div>',
            '  <div class="luwa-wa-modal-body">',
            '    <form id="luwaWaForm" onsubmit="return false;">',
            '      <div id="luwaWaFormFields">',
            '        <div class="mb-3">',
            '          <label class="form-label" for="luwaWaName"><i class="fas fa-user me-1 text-muted"></i> Your Name</label>',
            '          <input type="text" id="luwaWaName" class="form-control" placeholder="e.g. Douglas / Dr. Okello" required />',
            '        </div>',
            '        <div class="mb-3">',
            '          <label class="form-label" for="luwaWaPhone"><i class="fab fa-whatsapp me-1 text-success"></i> Your WhatsApp / Phone Number</label>',
            '          <input type="tel" id="luwaWaPhone" class="form-control" placeholder="e.g. +256 787 819 453" required />',
            '          <div class="form-text small text-muted">Our background engine will deliver your inquiry to the team and send an instant confirmation copy to this WhatsApp number.</div>',
            '        </div>',
            '        <div class="mb-4">',
            '          <label class="form-label" for="luwaWaMessage"><i class="fas fa-comment-alt me-1 text-muted"></i> Message</label>',
            '          <textarea id="luwaWaMessage" class="form-control" rows="3" required></textarea>',
            '        </div>',
            '        <div class="d-grid gap-2">',
            '          <button type="submit" id="luwaWaSubmitBtn" class="luwa-wa-btn-submit">',
            '            <i class="fas fa-paper-plane me-2"></i> Send via WhatsApp Background Engine',
            '          </button>',
            '          <button type="button" class="btn btn-link text-muted btn-sm" id="luwaWaCancelBtn">Cancel</button>',
            '        </div>',
            '      </div>',
            '      <div id="luwaWaSuccessBox" style="display:none; text-align:center; padding: 20px 10px;">',
            '        <div style="width:60px; height:60px; border-radius:50%; background:#ecfdf5; color:#10b981; display:inline-flex; align-items:center; justify-content:center; font-size:30px; margin-bottom:16px;">',
            '          <i class="fas fa-check"></i>',
            '        </div>',
            '        <h4 style="font-weight:700; color:#0b1628; margin-bottom:8px;">Message Delivered via WhatsApp Engine!</h4>',
            '        <p class="text-muted small" style="margin-bottom:20px;">',
            '          Your inquiry has been sent directly to the Luwa Tech solutions desk. An automated confirmation was also delivered to your WhatsApp number.',
            '        </p>',
            '        <button type="button" class="btn btn-outline-dark btn-sm px-4" id="luwaWaDoneBtn">Close</button>',
            '      </div>',
            '    </form>',
            '  </div>',
            '</div>'
        ].join("\n");

        document.body.appendChild(backdrop);

        // Bind Close Events
        function closeModal() {
            backdrop.classList.remove("is-active");
            var successBox = document.getElementById("luwaWaSuccessBox");
            var fieldsBox = document.getElementById("luwaWaFormFields");
            if (successBox) successBox.style.display = "none";
            if (fieldsBox) fieldsBox.style.display = "block";
        }

        document.getElementById("luwaWaCloseBtn").addEventListener("click", closeModal);
        document.getElementById("luwaWaCancelBtn").addEventListener("click", closeModal);
        document.getElementById("luwaWaDoneBtn").addEventListener("click", closeModal);
        backdrop.addEventListener("click", function (e) {
            if (e.target === backdrop) closeModal();
        });

        // Form Submission
        document.getElementById("luwaWaForm").addEventListener("submit", function (e) {
            e.preventDefault();
            var nameInput = document.getElementById("luwaWaName");
            var phoneInput = document.getElementById("luwaWaPhone");
            var messageInput = document.getElementById("luwaWaMessage");
            var submitBtn = document.getElementById("luwaWaSubmitBtn");

            var name = (nameInput.value || "").trim();
            var phone = (phoneInput.value || "").trim();
            var message = (messageInput.value || "").trim();

            if (!phone) {
                phoneInput.focus();
                showLuwaToast("Please enter your WhatsApp phone number", "error");
                return;
            }
            if (!message) {
                messageInput.focus();
                showLuwaToast("Please enter your message", "error");
                return;
            }

            // Save to localStorage for quick future usage
            try {
                localStorage.setItem("luwa_wa_name", name);
                localStorage.setItem("luwa_wa_phone", phone);
            } catch (err) {}

            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Sending in Background...';

            // Post to Odoo backend controller
            fetch("/luwatech/whatsapp/send_direct", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-Requested-With": "XMLHttpRequest",
                },
                body: JSON.stringify({
                    params: {
                        visitor_name: name,
                        visitor_phone: phone,
                        message: message,
                        source_url: window.location.href,
                    },
                }),
            })
                .then(function (res) {
                    return res.json();
                })
                .then(function (data) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i class="fas fa-paper-plane me-2"></i> Send via WhatsApp Background Engine';
                    var result = (data && data.result) ? data.result : data;
                    if (result && result.ok) {
                        document.getElementById("luwaWaFormFields").style.display = "none";
                        document.getElementById("luwaWaSuccessBox").style.display = "block";
                        showLuwaToast("Message dispatched via WhatsApp engine!", "success");
                        setTimeout(closeModal, 3500);
                    } else {
                        var errMsg = (result && result.error) || "Error sending message via WhatsApp bridge";
                        showLuwaToast(errMsg, "error");
                    }
                })
                .catch(function (err) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i class="fas fa-paper-plane me-2"></i> Send via WhatsApp Background Engine';
                    showLuwaToast("Network error. Please try again or call +256 787 819 453", "error");
                });
        });
    }

    function openWhatsAppModalWithMessage(defaultMessage) {
        ensureWhatsAppModal();
        var backdrop = document.getElementById("luwaWhatsAppModal");
        var nameInput = document.getElementById("luwaWaName");
        var phoneInput = document.getElementById("luwaWaPhone");
        var messageInput = document.getElementById("luwaWaMessage");

        if (nameInput) nameInput.value = localStorage.getItem("luwa_wa_name") || "";
        if (phoneInput) phoneInput.value = localStorage.getItem("luwa_wa_phone") || "";
        if (messageInput) messageInput.value = defaultMessage || "Hello Luwa Tech, I would like to make an inquiry.";

        backdrop.classList.add("is-active");
        if (phoneInput && !phoneInput.value) {
            phoneInput.focus();
        } else if (nameInput && !nameInput.value) {
            nameInput.focus();
        } else if (messageInput) {
            messageInput.focus();
        }
    }

    // Intercept all WhatsApp button clicks on the entire website
    document.addEventListener("click", function (e) {
        var waLink = e.target.closest('a[href*="wa.me"], a[href*="api.whatsapp.com"], a[href*="whatsapp.com"], .luwa-wa-btn');
        if (!waLink) return;

        e.preventDefault();
        e.stopPropagation();

        var href = waLink.getAttribute("href") || "";
        var extractedText = "";

        // Extract message from href text parameter
        try {
            var urlObj = new URL(href, window.location.origin);
            extractedText = urlObj.searchParams.get("text") || "";
        } catch (err) {
            var match = href.match(/[?&]text=([^&]+)/);
            if (match && match[1]) {
                extractedText = decodeURIComponent(match[1].replace(/\+/g, " "));
            }
        }

        if (!extractedText) {
            var linkText = waLink.textContent.trim();
            if (linkText.toLowerCase().indexOf("quote") !== -1) {
                extractedText = "Hello Luwa Tech, I would like to request an instant quote & demo.";
            } else if (linkText.toLowerCase().indexOf("subscription") !== -1) {
                extractedText = "Hello Luwa Tech, I need assistance with my subscription.";
            } else {
                extractedText = "Hello Luwa Tech, I would like to discuss a project with your team.";
            }
        }

        openWhatsAppModalWithMessage(extractedText);
    });

    // 3. Bidirectional appear/disappear scroll animations
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
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initLuwaAboutAnimations);
    } else {
        initLuwaAboutAnimations();
    }
})();
