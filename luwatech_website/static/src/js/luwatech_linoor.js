/**
 * Luwa Tech - Linoor Index-6 Interactive Behaviors & Bidirectional Scroll Animations
 * Handles: Hero Slider, Sticky Header, Mobile Menu, Search Popup, Animated Counters,
 * and Smooth Appearing/Disappearing Scroll Animations (Up & Down).
 */
(function () {
    "use strict";

    function initLuwaTechLinoor() {
        // 1. Sticky Header on Scroll
        var mainMenu = document.querySelector(".mainmenu-six");
        var scrollToTopBtn = document.querySelector(".scroll-to-top");

        function onScroll() {
            var scrollY = window.scrollY || window.pageYOffset;
            if (mainMenu) {
                if (scrollY > 120) {
                    mainMenu.classList.add("fixed-header");
                } else {
                    mainMenu.classList.remove("fixed-header");
                }
            }
            if (scrollToTopBtn) {
                scrollToTopBtn.style.display = scrollY > 300 ? "inline-block" : "none";
            }
        }
        window.addEventListener("scroll", onScroll, { passive: true });
        onScroll();

        // 2. Scroll to Top Click
        if (scrollToTopBtn) {
            scrollToTopBtn.addEventListener("click", function (e) {
                e.preventDefault();
                window.scrollTo({ top: 0, behavior: "smooth" });
            });
        }

        // 3. Mobile Nav Toggler
        var mobileTogglers = document.querySelectorAll(".mobile-nav-toggler, .side-menu__toggler, .side-menu__block-overlay");
        var sideMenuBlock = document.querySelector(".side-menu__block");
        mobileTogglers.forEach(function (btn) {
            btn.addEventListener("click", function (e) {
                e.preventDefault();
                if (sideMenuBlock) {
                    sideMenuBlock.classList.toggle("active");
                }
            });
        });

        // Close mobile drawer when clicking a link
        var mobileLinks = document.querySelectorAll(".mobile-nav__container a");
        mobileLinks.forEach(function (link) {
            link.addEventListener("click", function () {
                if (sideMenuBlock) {
                    sideMenuBlock.classList.remove("active");
                }
            });
        });

        // 4. Search Popup Toggler
        var searchTogglers = document.querySelectorAll(".search-toggler");
        var searchPopup = document.querySelector(".search-popup");
        searchTogglers.forEach(function (btn) {
            btn.addEventListener("click", function (e) {
                e.preventDefault();
                if (searchPopup) {
                    searchPopup.classList.toggle("active");
                }
            });
        });

        // 5. Hero Slider (slider-six) Auto & Manual Navigation
        var slides = document.querySelectorAll(".slider-six .swiper-slide");
        var prevBtn = document.getElementById("main-slider__swiper-button-prev");
        var nextBtn = document.getElementById("main-slider__swiper-button-next");
        var currentSlide = 0;
        var slideInterval = null;

        function showSlide(index) {
            if (!slides.length) return;
            slides.forEach(function (slide, i) {
                if (i === index) {
                    slide.classList.add("swiper-slide-active");
                    slide.style.display = "block";
                    slide.style.opacity = "1";
                } else {
                    slide.classList.remove("swiper-slide-active");
                    slide.style.opacity = "0";
                    slide.style.display = "none";
                }
            });
        }

        function nextSlide() {
            if (!slides.length) return;
            currentSlide = (currentSlide + 1) % slides.length;
            showSlide(currentSlide);
        }

        function prevSlide() {
            if (!slides.length) return;
            currentSlide = (currentSlide - 1 + slides.length) % slides.length;
            showSlide(currentSlide);
        }

        if (slides.length > 0) {
            showSlide(0);
            slideInterval = setInterval(nextSlide, 6500);

            if (nextBtn) {
                nextBtn.addEventListener("click", function () {
                    clearInterval(slideInterval);
                    nextSlide();
                    slideInterval = setInterval(nextSlide, 6500);
                });
            }
            if (prevBtn) {
                prevBtn.addEventListener("click", function () {
                    clearInterval(slideInterval);
                    prevSlide();
                    slideInterval = setInterval(nextSlide, 6500);
                });
            }
        }

        // 6. Bidirectional Scroll Reveal Animations (disabled while editing in Website Builder)
        var isEditorMode = document.body.classList.contains("editor_enable") || window.location.search.indexOf("enable_editor") !== -1;
        var revealSelectors = [
            ".about-seven__images",
            ".about-seven__content",
            ".sec-title-six",
            ".service-six__item",
            ".luwa-shop-card",
            ".subscribe-one .row",
            ".project-six__item",
            ".funfact-six__item",
            ".about-six__content",
            ".about-six__image",
            ".about-six__box",
            ".luwa-partner-card",
            ".blog-six__item",
            ".video-six__inner",
            ".luwa-footer-cta",
            ".luwa-footer-grid > div",
            ".oe_website_sale .o_wsale_product_grid_wrapper"
        ];

        var revealElements = isEditorMode ? [] : document.querySelectorAll(revealSelectors.join(", "));
        revealElements.forEach(function (el, idx) {
            el.classList.add("luwa-scroll-reveal");
            // Add subtle stagger within row siblings
            var parentRow = el.closest(".row");
            if (parentRow) {
                var siblings = Array.prototype.slice.call(parentRow.children);
                var colEl = el.closest("[class*='col-']") || el;
                var colIdx = siblings.indexOf(colEl);
                if (colIdx >= 0) {
                    el.style.transitionDelay = ((colIdx % 4) * 90) + "ms";
                }
            }
            // Check initial viewport visibility
            var rect = el.getBoundingClientRect();
            if (rect.top < window.innerHeight * 0.94 && rect.bottom > 0) {
                el.classList.add("is-visible");
            } else if (rect.top >= window.innerHeight * 0.94) {
                el.classList.add("is-hidden-below");
            } else {
                el.classList.add("is-hidden-above");
            }
        });

        if ("IntersectionObserver" in window && revealElements.length > 0) {
            var revealObserver = new IntersectionObserver(
                function (entries) {
                    entries.forEach(function (entry) {
                        var target = entry.target;
                        if (entry.isIntersecting) {
                            target.classList.add("is-visible");
                            target.classList.remove("is-hidden-below", "is-hidden-above");
                        } else {
                            // Remove .is-visible when scrolling out of view (up or down) so it re-animates smoothly
                            target.classList.remove("is-visible");
                            if (entry.boundingClientRect.top < 0) {
                                target.classList.add("is-hidden-above");
                                target.classList.remove("is-hidden-below");
                            } else {
                                target.classList.add("is-hidden-below");
                                target.classList.remove("is-hidden-above");
                            }
                        }
                    });
                },
                {
                    threshold: 0.12,
                    rootMargin: "-20px 0px -40px 0px"
                }
            );

            revealElements.forEach(function (el) {
                revealObserver.observe(el);
            });
        } else {
            revealElements.forEach(function (el) {
                el.classList.add("is-visible");
            });
        }

        // 7. Funfact Counter Animation (re-triggers on scroll)
        var counters = document.querySelectorAll(".count-text");
        function animateCounter(el) {
            var stop = parseInt(el.getAttribute("data-stop") || "100", 10);
            var speed = parseInt(el.getAttribute("data-speed") || "1200", 10);
            var start = 0;
            var stepTime = Math.max(Math.floor(speed / stop), 14);
            var timer = setInterval(function () {
                start += Math.max(1, Math.ceil(stop / 45));
                if (start >= stop) {
                    el.textContent = stop;
                    clearInterval(timer);
                } else {
                    el.textContent = start;
                }
            }, stepTime);
        }

        if ("IntersectionObserver" in window && counters.length > 0) {
            var counterObserver = new IntersectionObserver(
                function (entries) {
                    entries.forEach(function (entry) {
                        if (entry.isIntersecting) {
                            if (!entry.target.classList.contains("counted")) {
                                entry.target.classList.add("counted");
                                animateCounter(entry.target);
                            }
                        } else {
                            entry.target.classList.remove("counted");
                        }
                    });
                },
                { threshold: 0.25 }
            );
            counters.forEach(function (c) {
                counterObserver.observe(c);
            });
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initLuwaTechLinoor);
    } else {
        initLuwaTechLinoor();
    }
})();
