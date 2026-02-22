(() => {
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let resizeTimer = null;

  function setViewportHeightVar() {
    const vh = window.innerHeight * 0.01;
    document.documentElement.style.setProperty("--app-vh", `${vh}px`);
  }

  function applyResponsiveClasses() {
    const adminRoot = document.querySelector(".unfold");
    if (!adminRoot) return;

    const width = window.innerWidth;
    adminRoot.classList.toggle("admin-mobile-app", width <= 768);
    adminRoot.classList.toggle("admin-tablet-app", width > 768 && width <= 1279);
  }

  function updateScrollableState(wrapper) {
    if (!wrapper) return;

    const hasOverflow = wrapper.scrollWidth - wrapper.clientWidth > 6;
    wrapper.classList.toggle("has-overflow", hasOverflow);
    if (!hasOverflow) {
      wrapper.classList.remove("scroll-start", "scroll-end");
      return;
    }

    const atStart = wrapper.scrollLeft <= 3;
    const atEnd = wrapper.scrollLeft + wrapper.clientWidth >= wrapper.scrollWidth - 3;
    wrapper.classList.toggle("scroll-start", atStart);
    wrapper.classList.toggle("scroll-end", atEnd);
  }

  function enhanceScrollableResults() {
    const wrappers = document.querySelectorAll(".unfold .results");
    wrappers.forEach((wrapper) => {
      updateScrollableState(wrapper);
      if (wrapper.dataset.scrollBound === "1") return;

      wrapper.dataset.scrollBound = "1";
      wrapper.addEventListener("scroll", () => updateScrollableState(wrapper), { passive: true });
    });
  }

  function bindResponsiveWindowEvents() {
    if (window.__adminResponsiveEventsBound === true) return;
    window.__adminResponsiveEventsBound = true;

    const onResize = () => {
      if (resizeTimer) clearTimeout(resizeTimer);
      resizeTimer = window.setTimeout(() => {
        setViewportHeightVar();
        applyResponsiveClasses();
        enhanceScrollableResults();
      }, 120);
    };

    window.addEventListener("resize", onResize, { passive: true });
    window.addEventListener("orientationchange", onResize, { passive: true });
  }

  function revealCards() {
    const cards = document.querySelectorAll(
      ".unfold fieldset.module, .unfold .inline-group, .unfold .selector, .unfold #content-main > .module, .unfold #changelist .result-list-wrapper > .grow"
    );
    if (!cards.length) return;

    cards.forEach((card, index) => {
      card.classList.add("admin-reveal-target");
      card.style.setProperty("--reveal-delay", `${Math.min(index, 8) * 55}ms`);
    });

    if (prefersReducedMotion || !("IntersectionObserver" in window)) {
      cards.forEach((card) => card.classList.add("is-visible"));
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        });
      },
      {
        threshold: 0.08,
        rootMargin: "0px 0px -8% 0px",
      }
    );

    cards.forEach((card) => observer.observe(card));
  }

  function enhanceActionButtons() {
    const actionButtons = document.querySelectorAll(
      ".unfold button[type='submit'], .unfold input[type='submit'], .unfold a[class*='bg-primary-600']"
    );

    actionButtons.forEach((button) => {
      if (button.dataset.premiumBound === "1") return;
      button.dataset.premiumBound = "1";
      button.classList.add("premium-cta");

      button.addEventListener("pointerdown", (event) => {
        const rect = button.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;

        button.style.setProperty("--ripple-x", `${x}px`);
        button.style.setProperty("--ripple-y", `${y}px`);
        button.classList.remove("ripple-active");
        // Force reflow to restart ripple animation on every click.
        void button.offsetWidth;
        button.classList.add("ripple-active");
      });

      button.addEventListener("animationend", () => {
        button.classList.remove("ripple-active");
      });
    });
  }

  function markFocusedFields() {
    const fields = document.querySelectorAll(".unfold input, .unfold textarea, .unfold select");

    fields.forEach((field) => {
      if (field.dataset.focusBound === "1") return;
      field.dataset.focusBound = "1";

      const group = field.closest(".form-row, .field-box, .group");
      if (!group) return;

      field.addEventListener("focus", () => group.classList.add("admin-field-focus"));
      field.addEventListener("blur", () => group.classList.remove("admin-field-focus"));
    });
  }

  function animateListRows() {
    const rows = document.querySelectorAll(".unfold #changelist tbody tr, .unfold #result_list tbody tr");
    rows.forEach((row, index) => {
      row.style.setProperty("--row-delay", `${Math.min(index, 12) * 24}ms`);
      if (!prefersReducedMotion) row.classList.add("admin-row-entry");
    });
  }

  function initAdminEffects() {
    setViewportHeightVar();
    applyResponsiveClasses();
    enhanceScrollableResults();
    bindResponsiveWindowEvents();
    revealCards();
    enhanceActionButtons();
    markFocusedFields();
    animateListRows();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAdminEffects, { once: true });
  } else {
    initAdminEffects();
  }

  document.addEventListener("htmx:afterSwap", initAdminEffects);
})();
