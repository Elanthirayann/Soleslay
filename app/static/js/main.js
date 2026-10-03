(function () {
  "use strict";

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ------------------------------------------------------------------
     Mobile menu: full-screen slide-down drawer with backdrop, focus
     handling, Escape-to-close, background-scroll lock and accordions.
     ------------------------------------------------------------------ */
  var toggle = document.getElementById("mobile-menu-toggle");
  var menu = document.getElementById("mobile-menu");
  var backdrop = document.getElementById("mobile-menu-backdrop");
  var closeBtn = document.getElementById("mobile-menu-close");

  function openMobileMenu() {
    if (!menu) { return; }
    menu.classList.add("is-open");
    menu.setAttribute("aria-hidden", "false");
    if (backdrop) {
      backdrop.hidden = false;
      requestAnimationFrame(function () { backdrop.classList.add("is-open"); });
    }
    if (toggle) { toggle.setAttribute("aria-expanded", "true"); }
    document.body.classList.add("mobile-menu-open");
    if (closeBtn) { closeBtn.focus(); }
  }

  function closeMobileMenu() {
    if (!menu) { return; }
    menu.classList.remove("is-open");
    menu.setAttribute("aria-hidden", "true");
    if (backdrop) {
      backdrop.classList.remove("is-open");
      window.setTimeout(function () { backdrop.hidden = true; }, reduceMotion ? 0 : 250);
    }
    if (toggle) {
      toggle.setAttribute("aria-expanded", "false");
      toggle.focus();
    }
    document.body.classList.remove("mobile-menu-open");
  }

  if (toggle && menu) {
    toggle.addEventListener("click", function () {
      var isOpen = menu.classList.contains("is-open");
      if (isOpen) { closeMobileMenu(); } else { openMobileMenu(); }
    });
  }
  if (closeBtn) { closeBtn.addEventListener("click", closeMobileMenu); }
  if (backdrop) { backdrop.addEventListener("click", closeMobileMenu); }

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && menu && menu.classList.contains("is-open")) {
      closeMobileMenu();
    }
  });

  /* Mobile accordions (Men / Women) */
  document.querySelectorAll(".mobile-accordion-trigger").forEach(function (trigger) {
    var panelId = trigger.getAttribute("aria-controls");
    var panel = panelId ? document.getElementById(panelId) : null;
    if (!panel) { return; }
    trigger.addEventListener("click", function () {
      var isOpen = trigger.getAttribute("aria-expanded") === "true";
      trigger.setAttribute("aria-expanded", isOpen ? "false" : "true");
      panel.setAttribute("aria-hidden", isOpen ? "true" : "false");
      panel.classList.toggle("is-open", !isOpen);
    });
  });

  /* ------------------------------------------------------------------
     Desktop mega menus (Men / Women): hover-intent open, click toggle,
     Escape to close, click-outside to close, keyboard accessible.
     ------------------------------------------------------------------ */
  var navItems = document.querySelectorAll(".nav-item.has-mega");
  var openHoverTimer = null;
  var closeHoverTimer = null;

  function closeAllMegaMenus(exceptTrigger) {
    navItems.forEach(function (item) {
      var trigger = item.querySelector(".nav-mega-trigger");
      var mega = item.querySelector(".mega-menu");
      if (trigger === exceptTrigger) { return; }
      if (trigger) { trigger.setAttribute("aria-expanded", "false"); }
      if (mega) { mega.classList.remove("is-open"); }
    });
  }

  navItems.forEach(function (item) {
    var trigger = item.querySelector(".nav-mega-trigger");
    var mega = item.querySelector(".mega-menu");
    if (!trigger || !mega) { return; }

    function open() {
      closeAllMegaMenus(trigger);
      trigger.setAttribute("aria-expanded", "true");
      mega.classList.add("is-open");
    }

    function close() {
      trigger.setAttribute("aria-expanded", "false");
      mega.classList.remove("is-open");
    }

    trigger.addEventListener("click", function () {
      var isOpen = trigger.getAttribute("aria-expanded") === "true";
      if (isOpen) { close(); } else { open(); }
    });

    item.addEventListener("mouseenter", function () {
      window.clearTimeout(closeHoverTimer);
      openHoverTimer = window.setTimeout(open, 90);
    });

    item.addEventListener("mouseleave", function () {
      window.clearTimeout(openHoverTimer);
      closeHoverTimer = window.setTimeout(close, 150);
    });
  });

  document.addEventListener("click", function (e) {
    var withinMega = e.target.closest && e.target.closest(".nav-item.has-mega");
    if (!withinMega) { closeAllMegaMenus(); }
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") { closeAllMegaMenus(); }
  });

  /* ------------------------------------------------------------------
     Desktop search toggle: reveals the inline search form under the
     header without navigating away or requiring JavaScript to submit.
     ------------------------------------------------------------------ */
  var searchToggle = document.getElementById("nav-search-toggle");
  var searchForm = document.getElementById("nav-search-form");
  if (searchToggle && searchForm) {
    searchToggle.addEventListener("click", function () {
      var isOpen = !searchForm.hidden;
      searchForm.hidden = isOpen;
      searchToggle.setAttribute("aria-expanded", isOpen ? "false" : "true");
      if (!isOpen) {
        var input = searchForm.querySelector("input[name='q']");
        if (input) { input.focus(); }
      }
    });
  }

  /* Interactive hero spotlight: clicking a thumbnail swaps the featured
     product's image, name, description, price and buttons with a quick
      crossfade. Falls back to plain state changes (no fade) when the
      visitor prefers reduced motion. */
  var heroSection = document.querySelector("[data-hero-section]");

  if (heroSection) {
    var thumbs = heroSection.querySelectorAll("[data-hero-thumb]");
    var infoPanel = heroSection.querySelector("[data-hero-info]");
    var image = heroSection.querySelector("[data-hero-image]");
    var brandEl = heroSection.querySelector("[data-hero-brand]");
    var nameEl = heroSection.querySelector("[data-hero-name]");
    var descEl = heroSection.querySelector("[data-hero-desc]");
    var priceEl = heroSection.querySelector("[data-hero-price]");
    var tagEl = heroSection.querySelector("[data-hero-tag]");
    var buyBtn = heroSection.querySelector("[data-hero-buy]");
    var buyBtnText = heroSection.querySelector("[data-hero-buy-text]");
    var exploreBtn = heroSection.querySelector("[data-hero-explore]");
    var waNumber = (heroSection.getAttribute("data-wa-number") || "").replace(/\D/g, "");
    if (waNumber.length === 10) { waNumber = "91" + waNumber; }
    var heroReduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // --- In-Hero Size Availability Picker ---
    var sizePills = heroSection.querySelectorAll(".hero-size-pill");
    var sizeStatus = heroSection.querySelector("[data-hero-size-status]");
    var currentSize = 8;
    var currentProductName = (nameEl ? nameEl.textContent : "").trim() || "Sneakers";

    function formatPrice(rawPrice) {
      if (!rawPrice) { return "Ask in store"; }
      var num = parseInt(rawPrice, 10);
      if (isNaN(num)) { return "Ask in store"; }
      return "\u20b9" + num.toLocaleString("en-IN");
    }

    function updateWhatsAppCTA(name, size) {
      if (!name) { name = currentProductName; }
      if (buyBtnText) {
        buyBtnText.textContent = "Enquire UK " + size + " on WhatsApp";
      }
      if (buyBtn && waNumber) {
        var msg = "Hi Soleslay, I am looking for the " + name + " in size UK " + size + ". Is it available at your Guduvanchery store?";
        buyBtn.setAttribute("href", "https://wa.me/" + waNumber + "?text=" + encodeURIComponent(msg));
      }
    }

    sizePills.forEach(function (pill) {
      pill.addEventListener("click", function () {
        sizePills.forEach(function (p) {
          p.classList.remove("is-active");
          p.setAttribute("aria-checked", "false");
        });
        pill.classList.add("is-active");
        pill.setAttribute("aria-checked", "true");
        currentSize = pill.getAttribute("data-size") || "8";
        if (sizeStatus) {
          sizeStatus.textContent = "In Store · Size UK " + currentSize + " Ready";
        }
        updateWhatsAppCTA(currentProductName, currentSize);
      });
    });

    // --- 3D Volumetric Sneaker Inspection Engine (Gimbal Tilt, Specular Sheen & Parallax) ---
    var turntableStage = heroSection.querySelector("[data-hero-turntable]");
    var turntableRig = heroSection.querySelector("[data-turntable-rig]");
    var sneakerWrap = heroSection.querySelector("[data-turntable-sneaker-wrap]");
    var dialAngle = heroSection.querySelector("[data-dial-angle]");
    var dialPresets = heroSection.querySelectorAll("[data-view-preset]");
    var hotspots = heroSection.querySelectorAll("[data-hotspot]");

    // Perspective Gimbal State (bounded within realistic viewing frustum)
    var targetYaw = 0;      // -32deg to +32deg
    var targetPitch = 0;    // -18deg to +18deg
    var currentYaw = 0;
    var currentPitch = 0;
    var currentRoll = 0;
    var isDragging = false;
    var isHovering = false;
    var lastPointerX = 0;
    var lastPointerY = 0;
    var activePresetKey = "lateral";

    // Viewpoint presets dictionary
    var PRESET_VIEWS = {
      lateral: { yaw: 0, pitch: 0, name: "Lateral Profile" },
      top:     { yaw: -8, pitch: 16, name: "Top Collar 3D" },
      toe:     { yaw: 24, pitch: 8, name: "Toe-Box 3D" },
      sole:    { yaw: 16, pitch: -14, name: "Midsole Cushion" },
      reset:   { yaw: 0, pitch: 0, name: "3D Perspective" }
    };

    function updateActivePresetButton(key) {
      activePresetKey = key;
      dialPresets.forEach(function (btn) {
        var p = btn.getAttribute("data-view-preset");
        btn.classList.toggle("is-active", p === key);
      });
      if (dialAngle && PRESET_VIEWS[key]) {
        dialAngle.textContent = PRESET_VIEWS[key].name;
      }
    }

    if (turntableStage && turntableRig) {
      function setRigVariables(yaw, pitch, roll) {
        // Specular dynamic light tracking across 3D curves
        var sheenX = 50 + (yaw / 32) * 28;
        var sheenY = 38 - (pitch / 18) * 22;

        // Ground shadow deformation
        var shadowX = yaw * -0.75;
        var shadowY = pitch * 0.45;
        var shadowSx = 1 + Math.abs(yaw) * 0.005;
        var shadowSy = 1 - Math.abs(pitch) * 0.008;
        var shadowBlur = 9 + Math.abs(pitch) * 0.25;
        var shadowOpacity = 0.85 - Math.abs(pitch) * 0.008;

        turntableRig.style.setProperty("--yaw", yaw.toFixed(2) + "deg");
        turntableRig.style.setProperty("--pitch", pitch.toFixed(2) + "deg");
        turntableRig.style.setProperty("--roll", roll.toFixed(2) + "deg");
        turntableRig.style.setProperty("--yaw-num", yaw.toFixed(2));
        turntableRig.style.setProperty("--pitch-num", pitch.toFixed(2));
        turntableRig.style.setProperty("--sheen-x", sheenX.toFixed(1) + "%");
        turntableRig.style.setProperty("--sheen-y", sheenY.toFixed(1) + "%");
        turntableRig.style.setProperty("--shadow-x", shadowX.toFixed(1) + "px");
        turntableRig.style.setProperty("--shadow-y", shadowY.toFixed(1) + "px");
        turntableRig.style.setProperty("--shadow-sx", shadowSx.toFixed(3));
        turntableRig.style.setProperty("--shadow-sy", shadowSy.toFixed(3));
        turntableRig.style.setProperty("--shadow-blur", shadowBlur.toFixed(1) + "px");
        turntableRig.style.setProperty("--shadow-opacity", shadowOpacity.toFixed(2));
      }

      // Smooth Physics Loop (LERP)
      function gimbalLoop() {
        if (!heroReduceMotion) {
          var ease = isDragging ? 0.28 : 0.08;
          currentYaw += (targetYaw - currentYaw) * ease;
          currentPitch += (targetPitch - currentPitch) * ease;
          currentRoll = currentYaw * -0.06;
          setRigVariables(currentYaw, currentPitch, currentRoll);
        }
        requestAnimationFrame(gimbalLoop);
      }

      requestAnimationFrame(gimbalLoop);

      // Desktop Hover Parallax (smoothly tracks cursor when moving over stage)
      turntableStage.addEventListener("pointerenter", function () {
        isHovering = true;
      });

      turntableStage.addEventListener("pointerleave", function () {
        isHovering = false;
        if (!isDragging && activePresetKey === "lateral") {
          targetYaw = 0;
          targetPitch = 0;
        }
      });

      turntableStage.addEventListener("pointermove", function (e) {
        if (isDragging) {
          var dx = e.clientX - lastPointerX;
          var dy = e.clientY - lastPointerY;
          lastPointerX = e.clientX;
          lastPointerY = e.clientY;

          targetYaw = Math.max(-32, Math.min(32, targetYaw + dx * 0.38));
          targetPitch = Math.max(-18, Math.min(18, targetPitch - dy * 0.28));

          // Deselect presets when manually dragging to custom angles
          if (Math.abs(targetYaw) > 3 || Math.abs(targetPitch) > 3) {
            if (activePresetKey !== "custom") {
              activePresetKey = "custom";
              dialPresets.forEach(function (btn) { btn.classList.remove("is-active"); });
              if (dialAngle) { dialAngle.textContent = Math.round(targetYaw) + "\u00b0 Custom Tilt"; }
            }
          }
        } else if (isHovering && !heroReduceMotion && e.pointerType === "mouse") {
          // Subtle natural mouse-tracking tilt
          var rect = turntableStage.getBoundingClientRect();
          var relX = (e.clientX - (rect.left + rect.width / 2)) / (rect.width / 2);
          var relY = (e.clientY - (rect.top + rect.height / 2)) / (rect.height / 2);

          if (activePresetKey === "lateral" || activePresetKey === "reset") {
            targetYaw = Math.max(-20, Math.min(20, relX * 20));
            targetPitch = Math.max(-14, Math.min(14, -relY * 14));
          }
        }
      });

      // Pointer Drag Start
      turntableStage.addEventListener("pointerdown", function (e) {
        if (e.pointerType === "mouse" && e.button !== 0) return;
        // Don't intercept clicks on hotspot pins or dial buttons
        if (e.target.closest(".hero-3d-pin") || e.target.closest(".hero-turntable-dial")) return;

        isDragging = true;
        lastPointerX = e.clientX;
        lastPointerY = e.clientY;
        turntableStage.classList.add("is-dragging");
        if (sneakerWrap) sneakerWrap.classList.remove("is-levitating");
        turntableStage.setPointerCapture(e.pointerId);
      });

      function onPointerUp(e) {
        if (!isDragging) return;
        isDragging = false;
        turntableStage.classList.remove("is-dragging");
        try { turntableStage.releasePointerCapture(e.pointerId); } catch (err) {}
        if (sneakerWrap && !heroReduceMotion) {
          window.setTimeout(function () {
            if (!isDragging) sneakerWrap.classList.add("is-levitating");
          }, 600);
        }
      }

      turntableStage.addEventListener("pointerup", onPointerUp);
      turntableStage.addEventListener("pointercancel", onPointerUp);

      // Viewpoint Preset Click Handlers
      dialPresets.forEach(function (btn) {
        btn.addEventListener("click", function (e) {
          e.preventDefault();
          e.stopPropagation();
          var presetKey = btn.getAttribute("data-view-preset");
          if (!PRESET_VIEWS[presetKey]) return;

          var view = PRESET_VIEWS[presetKey];
          targetYaw = view.yaw;
          targetPitch = view.pitch;
          updateActivePresetButton(presetKey);

          // Add brief spring class for smooth preset snap
          turntableRig.classList.add("is-animating");
          window.setTimeout(function () {
            turntableRig.classList.remove("is-animating");
          }, 600);
        });
      });

      // Hotspot interactive card popups
      hotspots.forEach(function (spot) {
        var pin = spot.querySelector(".hero-3d-pin");
        if (pin) {
          pin.addEventListener("click", function (e) {
            e.stopPropagation();
            var isOpen = spot.classList.contains("is-open");
            hotspots.forEach(function (s) { s.classList.remove("is-open"); });
            if (!isOpen) {
              spot.classList.add("is-open");
            }
          });
        }
      });

      document.addEventListener("click", function (e) {
        if (!e.target.closest(".hero-3d-hotspot")) {
          hotspots.forEach(function (s) { s.classList.remove("is-open"); });
        }
      });
    }

    function applyProduct(thumb) {
      var name = thumb.getAttribute("data-name") || "";
      var brand = thumb.getAttribute("data-brand") || "";
      var desc = thumb.getAttribute("data-desc") || "";
      var price = thumb.getAttribute("data-price") || "";
      var tag = thumb.getAttribute("data-tag") || "";
      var imgSrc = thumb.getAttribute("data-image") || "";
      var imgAlt = thumb.getAttribute("data-alt") || name;
      var slug = thumb.getAttribute("data-slug") || "";
      var ctaLabel = thumb.getAttribute("data-cta-label") || "";
      var ctaUrl = thumb.getAttribute("data-cta-url") || "";

      currentProductName = name;

      if (brandEl) { brandEl.textContent = brand; }
      if (nameEl) { nameEl.textContent = name; }
      if (descEl) { descEl.textContent = "\u201c" + desc + "\u2026\u201d"; }
      if (priceEl) { priceEl.textContent = formatPrice(price); }
      if (tagEl) { tagEl.textContent = tag; }
      if (exploreBtn) {
        exploreBtn.setAttribute("href", ctaUrl || (slug ? "/products/" + slug : "#"));
        exploreBtn.textContent = ctaLabel || "Explore Collection";
      }

      updateWhatsAppCTA(currentProductName, currentSize);

      // Reset tilt angles to lateral view smoothly on shoe switch
      targetYaw = 0;
      targetPitch = 0;
      updateActivePresetButton("lateral");

      if (image && imgSrc) {
        if (heroReduceMotion) {
          image.setAttribute("src", imgSrc);
          image.setAttribute("alt", imgAlt);
        } else {
          image.classList.add("is-swapping");
          window.setTimeout(function () {
            image.setAttribute("src", imgSrc);
            image.setAttribute("alt", imgAlt);
            image.classList.remove("is-swapping");
          }, 180);
        }
      }

      if (infoPanel && !heroReduceMotion) {
        infoPanel.style.animation = "none";
        void infoPanel.offsetWidth;
        infoPanel.style.animation = "";
      }
    }

    thumbs.forEach(function (thumb) {
      thumb.addEventListener("click", function () {
        if (thumb.classList.contains("is-active")) { return; }
        var index = Array.prototype.indexOf.call(thumbs, thumb);
        thumbs.forEach(function (t) {
          t.classList.remove("is-active");
          t.setAttribute("aria-selected", "false");
        });
        thumb.classList.add("is-active");
        thumb.setAttribute("aria-selected", "true");
        applyProduct(thumb);

        var dots = heroSection.querySelectorAll("[data-hero-dot]");
        dots.forEach(function (dot, i) {
          dot.classList.toggle("is-active", i === index);
        });
      });
    });
  }

  /* ------------------------------------------------------------------
     Scroll-reveal for homepage sections. Skips straight to the visible
     state when the visitor prefers reduced motion, or when
     IntersectionObserver isn't supported.
     ------------------------------------------------------------------ */
  var revealEls = document.querySelectorAll("[data-reveal]");
  if (revealEls.length) {
    if (reduceMotion || !("IntersectionObserver" in window)) {
      revealEls.forEach(function (el) { el.classList.add("is-revealed"); });
    } else {
      var revealObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-revealed");
            revealObserver.unobserve(entry.target);
          }
        });
      }, { threshold: 0.01, rootMargin: "250px 0px 250px 0px" });
      revealEls.forEach(function (el) { revealObserver.observe(el); });
    }
  }

  /* ------------------------------------------------------------------
     Store media video: plays with sound on explicit user interaction.
     Includes interactive sound/mute toggle button and state updates.
     ------------------------------------------------------------------ */
  var storeVideo = document.querySelector("[data-store-video]");
  var videoToggle = document.querySelector("[data-video-toggle]");
  var soundToggle = document.querySelector("[data-video-sound-toggle]");
  if (storeVideo && videoToggle) {
    function updateSoundUI() {
      if (!soundToggle) return;
      var isMuted = storeVideo.muted || storeVideo.volume === 0;
      soundToggle.classList.toggle("is-muted", isMuted);
      soundToggle.setAttribute("aria-label", isMuted ? "Unmute video sound" : "Mute video sound");
      var textEl = soundToggle.querySelector(".store-media-sound-text");
      if (textEl) {
        textEl.textContent = isMuted ? "Unmute" : "Sound On";
      }
    }

    function playVideoWithSound() {
      // Ensure sound is active and unmuted on user play
      storeVideo.muted = false;
      storeVideo.volume = 1.0;
      updateSoundUI();
      var playPromise = storeVideo.play();
      if (playPromise !== undefined) {
        playPromise.then(function () {
          videoToggle.hidden = true;
        }).catch(function (err) {
          // Fallback if browser requires muted initial start
          storeVideo.muted = true;
          updateSoundUI();
          storeVideo.play().then(function () {
            videoToggle.hidden = true;
          });
        });
      }
    }

    function togglePlay(e) {
      // If clicking sound toggle, don't toggle play/pause
      if (soundToggle && (e.target === soundToggle || soundToggle.contains(e.target))) {
        return;
      }
      if (storeVideo.paused) {
        playVideoWithSound();
      } else {
        storeVideo.pause();
        videoToggle.hidden = false;
      }
    }

    if (soundToggle) {
      soundToggle.addEventListener("click", function (e) {
        e.stopPropagation();
        storeVideo.muted = !storeVideo.muted;
        if (!storeVideo.muted && storeVideo.volume === 0) {
          storeVideo.volume = 1.0;
        }
        updateSoundUI();
        if (storeVideo.paused) {
          storeVideo.play().then(function () {
            videoToggle.hidden = true;
          });
        }
      });
    }

    videoToggle.addEventListener("click", togglePlay);
    storeVideo.addEventListener("click", togglePlay);
    storeVideo.addEventListener("pause", function () {
      videoToggle.hidden = false;
    });
    storeVideo.addEventListener("play", function () {
      videoToggle.hidden = true;
    });
    storeVideo.addEventListener("volumechange", updateSoundUI);

    // Initial state
    updateSoundUI();
  }

  /* ------------------------------------------------------------------
     Product listing: client-side filter (brand / new / featured) and
     sort, plus the mobile filter drawer. Operates on the already
     server-rendered cards (data-* attributes on each .product-card) so
     the full catalogue stays crawlable regardless of filter state —
     this never rewrites the URL or creates duplicate listing URLs.
     ------------------------------------------------------------------ */
  var grid = document.querySelector("[data-product-grid]");
  if (grid) {
    var cards = Array.prototype.slice.call(grid.querySelectorAll("[data-product-card]"));
    var originalOrder = cards.slice();
    var resultCount = document.querySelector("[data-result-count]");
    var noResults = document.getElementById("listing-no-results");
    var sortSelect = document.querySelector("[data-sort-select]");
    var filterChips = Array.prototype.slice.call(document.querySelectorAll(".filter-chip"));
    var filterCountBadge = document.getElementById("filter-count");

    var activeFilters = { brand: null, flags: [] };

    function cardMatches(card) {
      if (activeFilters.brand && card.getAttribute("data-brand") !== activeFilters.brand) {
        return false;
      }
      for (var i = 0; i < activeFilters.flags.length; i++) {
        var flag = activeFilters.flags[i];
        if (flag === "new" && card.getAttribute("data-new") !== "1") { return false; }
        if (flag === "featured" && card.getAttribute("data-featured") !== "1") { return false; }
      }
      return true;
    }

    function applySort(list) {
      var mode = sortSelect ? sortSelect.value : "featured";
      var sorted = list.slice();
      if (mode === "name") {
        sorted.sort(function (a, b) {
          return a.getAttribute("data-name").localeCompare(b.getAttribute("data-name"));
        });
      } else if (mode === "newest") {
        sorted.sort(function (a, b) {
          return Number(b.getAttribute("data-new")) - Number(a.getAttribute("data-new"));
        });
      } else if (mode === "price-asc" || mode === "price-desc") {
        sorted.sort(function (a, b) {
          var pa = a.getAttribute("data-price");
          var pb = b.getAttribute("data-price");
          var hasA = pa !== "";
          var hasB = pb !== "";
          if (!hasA && !hasB) { return 0; }
          if (!hasA) { return 1; }
          if (!hasB) { return -1; }
          var diff = parseFloat(pa) - parseFloat(pb);
          return mode === "price-asc" ? diff : -diff;
        });
      } else {
        sorted.sort(function (a, b) {
          return Number(b.getAttribute("data-featured")) - Number(a.getAttribute("data-featured"));
        });
      }
      return sorted;
    }

    /* Clean, User-Friendly Catalog Pagination Controller */
    var urlParams = new URLSearchParams(window.location.search);
    var currentPage = parseInt(urlParams.get("page"), 10) || 1;
    var perPageSetting = urlParams.get("per_page") || "9";

    var paginationWrapper = document.getElementById("listing-pagination-wrapper");
    var paginationNav = document.getElementById("pagination-nav");
    var paginationNumbers = document.getElementById("pagination-numbers");
    var prevBtn = document.getElementById("pagination-btn-prev");
    var nextBtn = document.getElementById("pagination-btn-next");
    var progressText = document.getElementById("pagination-showing-range");
    var totalCountEl = document.getElementById("pagination-total-count");
    var perPagePills = Array.prototype.slice.call(document.querySelectorAll(".perpage-pill"));

    function syncUrl() {
      if (!window.history || !window.history.replaceState) { return; }
      var currentUrl = new URL(window.location);
      if (currentPage > 1) {
        currentUrl.searchParams.set("page", String(currentPage));
      } else {
        currentUrl.searchParams.delete("page");
      }
      if (perPageSetting !== "9") {
        currentUrl.searchParams.set("per_page", perPageSetting);
      } else {
        currentUrl.searchParams.delete("per_page");
      }
      window.history.replaceState(null, "", currentUrl.toString());
    }

    function scrollToGridTop() {
      if (!grid) { return; }
      var rect = grid.getBoundingClientRect();
      var scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      var targetY = rect.top + scrollTop - 120;
      if (Math.abs(targetY - scrollTop) > 80) {
        window.scrollTo({ top: Math.max(0, targetY), behavior: "smooth" });
      }
    }

    function renderPaginationNumbers(totalPages) {
      if (!paginationNumbers) { return; }
      paginationNumbers.innerHTML = "";
      if (totalPages <= 1) { return; }

      var pages = [];
      if (totalPages <= 7) {
        for (var p = 1; p <= totalPages; p++) { pages.push(p); }
      } else {
        pages.push(1);
        if (currentPage > 3) { pages.push("..."); }
        var start = Math.max(2, currentPage - 1);
        var end = Math.min(totalPages - 1, currentPage + 1);
        for (var i = start; i <= end; i++) { pages.push(i); }
        if (currentPage < totalPages - 2) { pages.push("..."); }
        pages.push(totalPages);
      }

      pages.forEach(function (item) {
        if (item === "...") {
          var ellipsis = document.createElement("span");
          ellipsis.className = "catalog-page-ellipsis";
          ellipsis.textContent = "…";
          paginationNumbers.appendChild(ellipsis);
        } else {
          var btn = document.createElement("button");
          btn.type = "button";
          btn.className = "catalog-page-num" + (item === currentPage ? " is-active" : "");
          btn.textContent = String(item);
          btn.setAttribute("aria-label", "Go to page " + item);
          if (item === currentPage) {
            btn.setAttribute("aria-current", "page");
          }
          btn.addEventListener("click", function () {
            if (currentPage === item) return;
            currentPage = item;
            render();
            scrollToGridTop();
          });
          paginationNumbers.appendChild(btn);
        }
      });
    }

    function render() {
      var ordered = applySort(originalOrder);
      var matchingCards = ordered.filter(cardMatches);
      var totalMatching = matchingCards.length;

      var effectivePerPage = perPageSetting === "all" ? Math.max(1, totalMatching) : (parseInt(perPageSetting, 10) || 9);
      var totalPages = Math.max(1, Math.ceil(totalMatching / effectivePerPage));

      if (currentPage > totalPages) {
        currentPage = totalPages;
      }
      if (currentPage < 1) {
        currentPage = 1;
      }

      var startIndex = (currentPage - 1) * effectivePerPage;
      var endIndex = Math.min(startIndex + effectivePerPage, totalMatching);

      cards.forEach(function (card) { card.hidden = true; });

      for (var i = 0; i < matchingCards.length; i++) {
        var card = matchingCards[i];
        if (i >= startIndex && i < endIndex) {
          card.hidden = false;
        } else {
          card.hidden = true;
        }
        grid.appendChild(card);
      }

      if (resultCount) {
        resultCount.textContent = totalMatching + " " + (totalMatching === 1 ? "item" : "items");
      }
      if (noResults) {
        noResults.hidden = totalMatching !== 0;
      }
      if (filterCountBadge) {
        var activeCount = (activeFilters.brand ? 1 : 0) + activeFilters.flags.length;
        filterCountBadge.hidden = activeCount === 0;
        filterCountBadge.textContent = String(activeCount);
      }

      if (paginationWrapper) {
        if (totalMatching <= 0) {
          paginationWrapper.hidden = true;
        } else {
          paginationWrapper.hidden = false;
          
          var showingStart = totalMatching > 0 ? startIndex + 1 : 0;
          var showingEnd = endIndex;
          if (progressText) {
            progressText.textContent = showingStart + "–" + showingEnd;
          }
          if (totalCountEl) {
            totalCountEl.textContent = String(totalMatching);
          }

          if (perPagePills.length) {
            perPagePills.forEach(function (pill) {
              var val = pill.getAttribute("data-perpage-val");
              var isCurrent = val === perPageSetting;
              pill.classList.toggle("is-active", isCurrent);
              pill.setAttribute("aria-checked", String(isCurrent));
            });
          }

          if (paginationNav) {
            paginationNav.hidden = totalPages <= 1;
          }
          renderPaginationNumbers(totalPages);
          if (prevBtn) {
            prevBtn.disabled = currentPage <= 1;
          }
          if (nextBtn) {
            nextBtn.disabled = currentPage >= totalPages;
          }
        }
      }

      syncUrl();
    }

    if (prevBtn) {
      prevBtn.addEventListener("click", function () {
        if (currentPage > 1) {
          currentPage--;
          render();
          scrollToGridTop();
        }
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener("click", function () {
        var effectivePerPage = perPageSetting === "all" ? 1 : (parseInt(perPageSetting, 10) || 9);
        var totalMatching = originalOrder.filter(cardMatches).length;
        var totalPages = Math.ceil(totalMatching / effectivePerPage);
        if (currentPage < totalPages) {
          currentPage++;
          render();
          scrollToGridTop();
        }
      });
    }

    perPagePills.forEach(function (pill) {
      pill.addEventListener("click", function () {
        var val = pill.getAttribute("data-perpage-val");
        if (val === perPageSetting) return;
        perPageSetting = val;
        currentPage = 1;
        render();
        scrollToGridTop();
      });
    });

    window.addEventListener("popstate", function () {
      var params = new URLSearchParams(window.location.search);
      var pageFromUrl = parseInt(params.get("page"), 10) || 1;
      var perPageFromUrl = params.get("per_page") || "9";
      if (pageFromUrl !== currentPage || perPageFromUrl !== perPageSetting) {
        currentPage = pageFromUrl;
        perPageSetting = perPageFromUrl;
        render();
      }
    });

    if (sortSelect) {
      sortSelect.addEventListener("change", function () {
        currentPage = 1;
        render();
      });
    }

    filterChips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        var type = chip.getAttribute("data-filter-type");
        var value = chip.getAttribute("data-filter-value");
        var isActive = chip.classList.contains("is-active");

        if (type === "brand") {
          filterChips
            .filter(function (c) { return c.getAttribute("data-filter-type") === "brand"; })
            .forEach(function (c) {
              c.classList.remove("is-active");
              c.setAttribute("aria-pressed", "false");
            });
          activeFilters.brand = isActive ? null : value;
          if (!isActive) {
            chip.classList.add("is-active");
            chip.setAttribute("aria-pressed", "true");
          }
        } else if (type === "flag") {
          chip.classList.toggle("is-active", !isActive);
          chip.setAttribute("aria-pressed", String(!isActive));
          var idx = activeFilters.flags.indexOf(value);
          if (isActive && idx > -1) {
            activeFilters.flags.splice(idx, 1);
          } else if (!isActive && idx === -1) {
            activeFilters.flags.push(value);
          }
        }
        currentPage = 1;
        render();
      });
    });

    var clearBtn = document.getElementById("filter-clear");
    if (clearBtn) {
      clearBtn.addEventListener("click", function () {
        activeFilters = { brand: null, flags: [] };
        filterChips.forEach(function (c) {
          c.classList.remove("is-active");
          c.setAttribute("aria-pressed", "false");
        });
        currentPage = 1;
        render();
      });
    }

    /* Mobile filter drawer */
    var filterPanel = document.getElementById("listing-filter-panel");
    var filterToggle = document.getElementById("listing-filter-toggle");
    var filterClose = document.getElementById("filter-panel-close");
    var filterApply = document.getElementById("filter-apply");
    var filterBackdrop = document.getElementById("filter-drawer-backdrop");

    function openFilterPanel() {
      if (!filterPanel) { return; }
      filterPanel.classList.add("is-open");
      filterPanel.setAttribute("aria-hidden", "false");
      if (filterBackdrop) {
        filterBackdrop.hidden = false;
        requestAnimationFrame(function () { filterBackdrop.classList.add("is-open"); });
      }
      if (filterToggle) { filterToggle.setAttribute("aria-expanded", "true"); }
      document.body.classList.add("mobile-menu-open");
      if (filterClose) { filterClose.focus(); }
    }

    function closeFilterPanel() {
      if (!filterPanel) { return; }
      filterPanel.classList.remove("is-open");
      filterPanel.setAttribute("aria-hidden", "true");
      if (filterBackdrop) {
        filterBackdrop.classList.remove("is-open");
        window.setTimeout(function () { filterBackdrop.hidden = true; }, reduceMotion ? 0 : 250);
      }
      if (filterToggle) {
        filterToggle.setAttribute("aria-expanded", "false");
        filterToggle.focus();
      }
      document.body.classList.remove("mobile-menu-open");
    }

    if (filterToggle) { filterToggle.addEventListener("click", openFilterPanel); }
    if (filterClose) { filterClose.addEventListener("click", closeFilterPanel); }
    if (filterApply) { filterApply.addEventListener("click", closeFilterPanel); }
    if (filterBackdrop) { filterBackdrop.addEventListener("click", closeFilterPanel); }
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && filterPanel && filterPanel.classList.contains("is-open")) {
        closeFilterPanel();
      }
    });

    /* Pre-select brand from URL query params (e.g. ?brand=Nike) */
    try {
      var urlParams = new URLSearchParams(window.location.search);
      var brandParam = urlParams.get("brand");
      if (brandParam) {
        filterChips.forEach(function (c) {
          if (
            c.getAttribute("data-filter-type") === "brand" &&
            c.getAttribute("data-filter-value").toLowerCase() === brandParam.toLowerCase()
          ) {
            c.classList.add("is-active");
            c.setAttribute("aria-pressed", "true");
            activeFilters.brand = c.getAttribute("data-filter-value");
          }
        });
      }
    } catch (_) {}

    render();
  }

  /* ------------------------------------------------------------------
     Product gallery: sliding carousel track, mouse drag / touch swipe,
     prev/next arrows, thumbnail sync, and fullscreen inspect lightbox.
     ------------------------------------------------------------------ */
  var galleryEl = document.querySelector("[data-gallery]");
  if (galleryEl) {
    var galleryMain = galleryEl.querySelector("[data-gallery-main]");
    var galleryViewport = galleryEl.querySelector("[data-gallery-viewport]");
    var galleryTrack = galleryEl.querySelector("[data-gallery-track]");
    var gallerySlides = Array.prototype.slice.call(galleryEl.querySelectorAll(".gallery-slide"));
    var galleryThumbs = Array.prototype.slice.call(galleryEl.querySelectorAll(".thumb, .thumb-modern"));
    var prevBtn = galleryEl.querySelector("[data-gallery-prev]");
    var nextBtn = galleryEl.querySelector("[data-gallery-next]");
    var zoomBtn = galleryEl.querySelector("[data-gallery-zoom]");
    var counterCurrent = galleryEl.querySelector(".gallery-counter-current");
    var counterCaption = galleryEl.querySelector(".zine-counter-caption");
    var totalImages = gallerySlides.length || galleryThumbs.length || 1;
    var currentIndex = 0;

    /* Lightbox elements */
    var lightbox = document.getElementById("product-lightbox");
    var lightboxImage = document.getElementById("lightbox-image");
    var lightboxClose = document.getElementById("lightbox-close");
    var lightboxPrev = document.getElementById("lightbox-prev");
    var lightboxNext = document.getElementById("lightbox-next");
    var lightboxCounterCurrent = document.getElementById("lightbox-counter-current");
    var lightboxAngleTag = document.getElementById("lightbox-angle-tag");
    var lightboxThumbs = Array.prototype.slice.call(document.querySelectorAll("[data-lightbox-thumb-index]"));

    function showImage(index) {
      if (!totalImages) { return; }
      currentIndex = ((index % totalImages) + totalImages) % totalImages;

      /* Slide the carousel track smoothly */
      if (galleryTrack) {
        galleryTrack.style.transform = "translateX(-" + (currentIndex * 100) + "%)";
      }

      /* Update active slide */
      gallerySlides.forEach(function (slide, i) {
        slide.classList.toggle("is-active", i === currentIndex);
      });

      /* Update active lookbook thumbnail */
      galleryThumbs.forEach(function (t, i) {
        var active = i === currentIndex;
        t.classList.toggle("is-active", active);
        t.setAttribute("aria-selected", active ? "true" : "false");
      });

      /* Update counter number (e.g. 02) */
      if (counterCurrent) {
        counterCurrent.textContent = (currentIndex + 1 < 10 ? "0" : "") + (currentIndex + 1);
      }

      /* Update counter caption tag */
      var activeThumb = galleryThumbs[currentIndex];
      if (activeThumb && counterCaption) {
        var tileTag = activeThumb.querySelector(".zine-tile-tag");
        if (tileTag) {
          counterCaption.textContent = tileTag.textContent;
        }
      }

      /* If lightbox is currently open, sync it immediately */
      if (lightbox && lightbox.classList.contains("is-open")) {
        syncLightboxImage(currentIndex);
      }
    }

    /* Thumbnail click binding */
    galleryThumbs.forEach(function (thumb, i) {
      thumb.addEventListener("click", function () { showImage(i); });
    });

    /* Stage Prev/Next Arrow clicks */
    if (prevBtn) {
      prevBtn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        showImage(currentIndex - 1);
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        showImage(currentIndex + 1);
      });
    }

    /* Mouse Drag & Touch Swipe sliding gestures on the image stage */
    if (galleryViewport) {
      var isPointerDown = false;
      var startX = 0;
      var startY = 0;
      var currentDeltaX = 0;
      var hasMovedHorizontally = false;

      function onPointerDown(e) {
        // Ignore if clicking on navigation arrows or zoom button
        if (e.target.closest("[data-gallery-prev]") || e.target.closest("[data-gallery-next]") || e.target.closest("[data-gallery-zoom]")) {
          return;
        }

        isPointerDown = true;
        startX = e.clientX || (e.touches && e.touches[0].clientX) || 0;
        startY = e.clientY || (e.touches && e.touches[0].clientY) || 0;
        currentDeltaX = 0;
        hasMovedHorizontally = false;

        if (galleryTrack) {
          galleryTrack.style.transition = "none";
        }
        if (galleryViewport) {
          galleryViewport.classList.add("is-dragging");
        }
      }

      function onPointerMove(e) {
        if (!isPointerDown) { return; }

        var curX = e.clientX || (e.touches && e.touches[0].clientX) || 0;
        var curY = e.clientY || (e.touches && e.touches[0].clientY) || 0;
        currentDeltaX = curX - startX;
        var deltaY = curY - startY;

        // If mostly vertical scrolling on touch, let browser handle normal scroll
        if (!hasMovedHorizontally && Math.abs(deltaY) > Math.abs(currentDeltaX) && Math.abs(deltaY) > 8) {
          isPointerDown = false;
          if (galleryTrack) { galleryTrack.style.transition = ""; }
          if (galleryViewport) { galleryViewport.classList.remove("is-dragging"); }
          return;
        }

        if (Math.abs(currentDeltaX) > 6) {
          hasMovedHorizontally = true;
          if (e.cancelable) { e.preventDefault(); }
          if (galleryTrack && galleryViewport.offsetWidth) {
            var offsetPercent = -(currentIndex * 100) + (currentDeltaX / galleryViewport.offsetWidth) * 100;
            galleryTrack.style.transform = "translateX(" + offsetPercent + "%)";
          }
        }
      }

      function onPointerUp(e) {
        if (!isPointerDown) { return; }
        isPointerDown = false;
        if (galleryViewport) { galleryViewport.classList.remove("is-dragging"); }
        if (galleryTrack) { galleryTrack.style.transition = ""; }

        if (hasMovedHorizontally && Math.abs(currentDeltaX) > 40) {
          if (currentDeltaX < 0) {
            showImage(currentIndex + 1); // Dragged left -> next image
          } else {
            showImage(currentIndex - 1); // Dragged right -> prev image
          }
        } else if (!hasMovedHorizontally && Math.abs(currentDeltaX) < 10) {
          // Clean tap/click without drag -> Open full inspect lightbox!
          openLightbox(currentIndex);
        } else {
          // Drag was small -> snap back to current slide
          showImage(currentIndex);
        }
      }


      // Mouse & Touch events
      galleryViewport.addEventListener("mousedown", onPointerDown);
      window.addEventListener("mousemove", onPointerMove);
      window.addEventListener("mouseup", onPointerUp);

      galleryViewport.addEventListener("touchstart", onPointerDown, { passive: true });
      galleryViewport.addEventListener("touchmove", onPointerMove, { passive: false });
      galleryViewport.addEventListener("touchend", onPointerUp);
      galleryViewport.addEventListener("touchcancel", onPointerUp);
    }

    /* Keyboard navigation */
    if (galleryMain) {
      galleryMain.addEventListener("keydown", function (e) {
        if (e.key === "ArrowLeft") { showImage(currentIndex - 1); }
        if (e.key === "ArrowRight") { showImage(currentIndex + 1); }
        if (e.key === "Enter") { openLightbox(currentIndex); }
      });
    }

    /* ------------------------------------------------------------------
       Fullscreen Inspect Lightbox Modal
       ------------------------------------------------------------------ */
    function syncLightboxImage(index) {
      if (!lightbox || !galleryThumbs[index]) { return; }
      var activeThumb = galleryThumbs[index];
      var src = activeThumb.getAttribute("data-src");
      var alt = activeThumb.getAttribute("data-alt") || "";
      var tag = activeThumb.getAttribute("data-tag") || "";
      var tileTagEl = activeThumb.querySelector(".zine-tile-tag");
      if (tileTagEl) { tag = tileTagEl.textContent; }

      if (lightboxImage) {
        lightboxImage.setAttribute("src", src);
        lightboxImage.setAttribute("alt", alt);
      }
      if (lightboxCounterCurrent) {
        lightboxCounterCurrent.textContent = (index + 1 < 10 ? "0" : "") + (index + 1);
      }
      if (lightboxAngleTag) {
        lightboxAngleTag.textContent = tag;
      }
      lightboxThumbs.forEach(function (t, i) {
        t.classList.toggle("is-active", i === index);
      });
    }

    function openLightbox(index) {
      if (!lightbox) { return; }
      if (typeof index === "number") {
        currentIndex = index;
      }
      syncLightboxImage(currentIndex);
      lightbox.classList.add("is-open");
      lightbox.setAttribute("aria-hidden", "false");
      document.body.style.overflow = "hidden";
      if (lightboxClose) { lightboxClose.focus(); }
    }

    function closeLightbox() {
      if (!lightbox) { return; }
      lightbox.classList.remove("is-open");
      lightbox.setAttribute("aria-hidden", "true");
      document.body.style.overflow = "";
      if (zoomBtn) { zoomBtn.focus(); }
    }

    if (zoomBtn) {
      zoomBtn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        openLightbox(currentIndex);
      });
    }

    if (lightboxClose) {
      lightboxClose.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        closeLightbox();
      });
    }

    if (lightboxPrev) {
      lightboxPrev.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        showImage(currentIndex - 1);
      });
    }

    if (lightboxNext) {
      lightboxNext.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        showImage(currentIndex + 1);
      });
    }

    lightboxThumbs.forEach(function (thumb, i) {
      thumb.addEventListener("click", function () {
        showImage(i);
      });
    });

    if (lightbox) {
      lightbox.addEventListener("click", function (e) {
        // If clicked on backdrop (not inside image wrap or controls)
        if (e.target === lightbox || e.target.id === "lightbox-img-wrap") {
          closeLightbox();
        }
      });
    }

    document.addEventListener("keydown", function (e) {
      if (!lightbox || !lightbox.classList.contains("is-open")) { return; }
      if (e.key === "Escape") { closeLightbox(); }
      if (e.key === "ArrowLeft") { showImage(currentIndex - 1); }
      if (e.key === "ArrowRight") { showImage(currentIndex + 1); }
    });
  }

  /* ------------------------------------------------------------------
     Product detail size selector & Size Guide modal & Spec Tabs
     ------------------------------------------------------------------ */
  var sizeChips = Array.prototype.slice.call(document.querySelectorAll("[data-size-chip]"));
  if (sizeChips.length) {
    var enquiryBtn = document.querySelector("[data-enquiry-btn]");
    var enquiryIgBtn = document.querySelector("[data-enquiry-ig-btn]");
    var sizeNote = document.querySelector("[data-size-note]");
    var defaultHref = enquiryBtn ? enquiryBtn.getAttribute("href") : null;
    var defaultIgText = enquiryIgBtn ? enquiryIgBtn.getAttribute("data-ig-text") : null;

    sizeChips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        if (chip.disabled) { return; }
        var alreadySelected = chip.classList.contains("is-selected");
        sizeChips.forEach(function (c) {
          c.classList.remove("is-selected");
          c.setAttribute("aria-pressed", "false");
        });
        if (alreadySelected) {
          if (enquiryBtn && defaultHref) { enquiryBtn.setAttribute("href", defaultHref); }
          if (enquiryIgBtn && defaultIgText) { enquiryIgBtn.setAttribute("data-ig-text", defaultIgText); }
          if (sizeNote) { sizeNote.hidden = true; }
          return;
        }
        chip.classList.add("is-selected");
        chip.setAttribute("aria-pressed", "true");
        if (enquiryBtn) {
          var waUrl = chip.getAttribute("data-wa-url");
          if (waUrl) { enquiryBtn.setAttribute("href", waUrl); }
        }
        if (enquiryIgBtn) {
          var igText = chip.getAttribute("data-ig-text");
          if (igText) { enquiryIgBtn.setAttribute("data-ig-text", igText); }
        }
        if (sizeNote) {
          sizeNote.hidden = false;
          sizeNote.textContent = "Size " + chip.getAttribute("data-size") + " selected — ready to confirm.";
        }
      });
    });
  }

  /* Size Guide Modal */
  var sizeGuideBtn = document.getElementById("open-size-guide-btn");
  var sizeGuideModal = document.getElementById("size-guide-modal");
  var sizeGuideClose = document.getElementById("size-guide-close");
  var sizeGuideBackdrop = document.getElementById("size-guide-backdrop");

  function openSizeGuide() {
    if (!sizeGuideModal) { return; }
    sizeGuideModal.hidden = false;
    sizeGuideModal.setAttribute("aria-hidden", "false");
    requestAnimationFrame(function () {
      sizeGuideModal.classList.add("is-open");
    });
    document.body.classList.add("modal-open");
  }

  function closeSizeGuide() {
    if (!sizeGuideModal) { return; }
    sizeGuideModal.classList.remove("is-open");
    sizeGuideModal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("modal-open");
    window.setTimeout(function () {
      sizeGuideModal.hidden = true;
    }, 200);
  }

  if (sizeGuideBtn) { sizeGuideBtn.addEventListener("click", openSizeGuide); }
  if (sizeGuideClose) { sizeGuideClose.addEventListener("click", closeSizeGuide); }
  if (sizeGuideBackdrop) { sizeGuideBackdrop.addEventListener("click", closeSizeGuide); }

  /* Sourcing Concierge Modal */
  var sourcingModal = document.getElementById("sourcing-modal");
  var openSourcingBtn = document.getElementById("open-sourcing-modal-btn");
  var sourcingClose = document.getElementById("sourcing-modal-close");
  var sourcingBackdrop = document.getElementById("sourcing-modal-backdrop");
  var sourcingModelInput = document.getElementById("sourcing-model-input");
  var sourcingColorwaySelect = document.getElementById("sourcing-colorway-select");
  var sourcingSizeSelect = document.getElementById("sourcing-size-select");
  var sourcingNotesInput = document.getElementById("sourcing-notes-input");
  var sourcingWaSubmit = document.getElementById("sourcing-wa-submit");

  function updateSourcingWaUrl() {
    if (!sourcingWaSubmit) { return; }
    var model = sourcingModelInput ? sourcingModelInput.value : "Sneaker";
    var color = sourcingColorwaySelect ? sourcingColorwaySelect.value : "";
    var size = sourcingSizeSelect ? sourcingSizeSelect.value : "UK 8";
    var notes = sourcingNotesInput ? sourcingNotesInput.value.trim() : "";
    
    var msg = "Hi Soleslay Concierge! I want to request custom deadstock sourcing for:\n" +
              "• Model: " + model + "\n" +
              "• Colorway / Edition: " + color + "\n" +
              "• Size: " + size;
    if (notes) {
      msg += "\n• Note: " + notes;
    }
    msg += "\nCould you check your vault network for pricing and 48-72h sourcing availability?";
    sourcingWaSubmit.href = "https://wa.me/916374333780?text=" + encodeURIComponent(msg);
  }

  function openSourcingModal(presetColorway) {
    if (!sourcingModal) { return; }
    if (presetColorway && sourcingColorwaySelect) {
      for (var i = 0; i < sourcingColorwaySelect.options.length; i++) {
        if (sourcingColorwaySelect.options[i].value.indexOf(presetColorway) !== -1) {
          sourcingColorwaySelect.selectedIndex = i;
          break;
        }
      }
    }
    updateSourcingWaUrl();
    sourcingModal.hidden = false;
    sourcingModal.setAttribute("aria-hidden", "false");
    requestAnimationFrame(function () {
      sourcingModal.classList.add("is-open");
    });
    document.body.classList.add("modal-open");
  }

  function closeSourcingModal() {
    if (!sourcingModal) { return; }
    sourcingModal.classList.remove("is-open");
    sourcingModal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("modal-open");
    window.setTimeout(function () {
      sourcingModal.hidden = true;
    }, 200);
  }

  if (openSourcingBtn) {
    openSourcingBtn.addEventListener("click", function () { openSourcingModal(); });
  }
  if (sourcingClose) { sourcingClose.addEventListener("click", closeSourcingModal); }
  if (sourcingBackdrop) { sourcingBackdrop.addEventListener("click", closeSourcingModal); }

  if (sourcingColorwaySelect) { sourcingColorwaySelect.addEventListener("change", updateSourcingWaUrl); }
  if (sourcingSizeSelect) { sourcingSizeSelect.addEventListener("change", updateSourcingWaUrl); }
  if (sourcingNotesInput) { sourcingNotesInput.addEventListener("input", updateSourcingWaUrl); }

  document.querySelectorAll("[data-sourcing-trigger]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var colorway = btn.getAttribute("data-colorway");
      openSourcingModal(colorway);
    });
  });

  /* PDP Specification Tabs */
  var tabTriggers = Array.prototype.slice.call(document.querySelectorAll(".pdp-tab-trigger"));
  if (tabTriggers.length) {
    tabTriggers.forEach(function (trigger) {
      trigger.addEventListener("click", function () {
        var targetId = trigger.getAttribute("aria-controls");
        var targetPanel = document.getElementById(targetId);
        if (!targetPanel) { return; }

        tabTriggers.forEach(function (t) {
          t.classList.remove("is-active");
          t.setAttribute("aria-selected", "false");
        });
        document.querySelectorAll(".pdp-tab-panel").forEach(function (p) {
          p.classList.remove("is-active");
          p.hidden = true;
        });

        trigger.classList.add("is-active");
        trigger.setAttribute("aria-selected", "true");
        targetPanel.hidden = false;
        targetPanel.classList.add("is-active");
      });
    });
  }
})();

/* ===========================================================================
   ADVANCED UI — magnetic buttons, spring-press taps, skeleton removal,
   quick-view panel, gallery crossfade, sticky mobile buy bar, hero
   parallax + word-stagger trigger. Kept as its own IIFE so it can be
   read/maintained independently of the block above. Respects
   prefers-reduced-motion throughout, same as the rest of the file.
   =========================================================================== */
(function () {
  "use strict";

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var hasFinePointer = window.matchMedia("(hover: hover) and (pointer: fine)").matches;

  /* ------------------------------------------------------------------
     1. Magnetic buttons (desktop, fine pointer only): primary CTAs and
     the quick-view trigger drift a few px toward the cursor as it
     nears, and spring back on leave via the CSS transition already
     defined on [data-magnetic].
     ------------------------------------------------------------------ */
  if (hasFinePointer && !reduceMotion) {
    var magneticEls = document.querySelectorAll("[data-magnetic]");
    magneticEls.forEach(function (el) {
      var strength = 0.35;
      el.addEventListener("mousemove", function (e) {
        var rect = el.getBoundingClientRect();
        var relX = e.clientX - (rect.left + rect.width / 2);
        var relY = e.clientY - (rect.top + rect.height / 2);
        el.style.transform = "translate(" + (relX * strength) + "px, " + (relY * strength) + "px)";
      });
      el.addEventListener("mouseleave", function () {
        el.style.transform = "translate(0, 0)";
      });
    });
  }

  /* ------------------------------------------------------------------
     2. Spring-press taps: any .btn or .size-chip gets a short bounce
     keyframe on press, via a class toggled for the animation's
     duration. Uses 'animationend' rather than a timeout so it never
     drifts out of sync with the CSS.
     ------------------------------------------------------------------ */
  if (!reduceMotion) {
    document.addEventListener("pointerdown", function (e) {
      var target = e.target.closest && e.target.closest(".btn, .size-chip");
      if (!target || target.disabled) { return; }
      target.classList.remove("is-spring-pressed");
      // Force reflow so re-adding the class restarts the animation on
      // rapid repeated taps.
      void target.offsetWidth;
      target.classList.add("is-spring-pressed");
    });
    document.addEventListener("animationend", function (e) {
      if (e.animationName === "spring-press") {
        e.target.classList.remove("is-spring-pressed");
      }
    });
  }

  /* ------------------------------------------------------------------
     3. Skeleton shimmer: every product image gets a shimmering
     placeholder (already painted server-side via .img-skeleton) that's
     removed the instant its image finishes loading — or immediately if
     the image was already cached/complete by the time this runs.
     ------------------------------------------------------------------ */
  document.querySelectorAll("[data-skeleton-wrap]").forEach(function (wrap) {
    var img = wrap.querySelector("img");
    var skeleton = wrap.querySelector(".img-skeleton");
    if (!img || !skeleton) { return; }
    function reveal() { skeleton.classList.add("is-loaded"); }
    if (img.complete && img.naturalWidth > 0) {
      reveal();
    } else {
      img.addEventListener("load", reveal, { once: true });
      img.addEventListener("error", reveal, { once: true });
    }
  });

  /* ------------------------------------------------------------------
     4. Quick-view panel: tapping a card's quick-view trigger opens a
     slide-up (mobile) / pop-up (desktop) summary — image, name, brand,
     price, size availability and an Enquire button — read entirely
     from the card's own data-* attributes, so no extra network request
     is needed and the underlying grid stays exactly as crawlable as
     before.
     ------------------------------------------------------------------ */
  var qvPanel = document.getElementById("quickview-panel");
  var qvBackdrop = document.getElementById("quickview-backdrop");
  if (qvPanel && qvBackdrop) {
    var qvImage = qvPanel.querySelector("[data-qv-image]");
    var qvBrand = qvPanel.querySelector("[data-qv-brand]");
    var qvName = qvPanel.querySelector("[data-qv-name]");
    var qvPrice = qvPanel.querySelector("[data-qv-price]");
    var qvAvailability = qvPanel.querySelector("[data-qv-availability]");
    var qvSizes = qvPanel.querySelector("[data-qv-sizes]");
    var qvViewLink = qvPanel.querySelector("[data-qv-view-link]");
    var qvWaLink = qvPanel.querySelector("[data-qv-wa-link]");
    var qvIgLink = qvPanel.querySelector("[data-qv-ig-link]");
    var qvClose = qvPanel.querySelector("[data-qv-close]");
    var qvLastTrigger = null;

    function openQuickView(trigger) {
      var card = trigger.closest("[data-product-card]");
      if (!card) { return; }
      qvLastTrigger = trigger;

      var img = card.querySelector(".product-card-img--primary, img");
      if (qvImage && img) {
        qvImage.setAttribute("src", img.getAttribute("src"));
        qvImage.setAttribute("alt", img.getAttribute("alt") || "");
      }
      if (qvBrand) { qvBrand.textContent = card.getAttribute("data-brand") || ""; }
      if (qvName) { qvName.textContent = card.getAttribute("data-name") || ""; }
      if (qvPrice) {
        var price = card.getAttribute("data-price");
        qvPrice.textContent = price ? ("\u20B9" + Number(price).toLocaleString("en-IN")) : "Enquire for price";
      }
      if (qvAvailability) {
        qvAvailability.textContent = card.getAttribute("data-availability-label") || "";
      }
      if (qvSizes) {
        qvSizes.innerHTML = "";
        var sizesRaw = card.getAttribute("data-sizes");
        var sizes = [];
        try { sizes = sizesRaw ? JSON.parse(sizesRaw) : []; } catch (err) { sizes = []; }
        sizes.forEach(function (s) {
          var pill = document.createElement("span");
          pill.className = "quickview-size-pill" + (s.available ? "" : " is-unavailable");
          pill.textContent = s.size;
          qvSizes.appendChild(pill);
        });
        qvSizes.hidden = sizes.length === 0;
      }
      if (qvViewLink) { qvViewLink.setAttribute("href", card.getAttribute("data-detail-url") || "#"); }
      if (qvWaLink) { qvWaLink.setAttribute("href", card.getAttribute("data-wa-link") || "#"); }
      if (qvIgLink) {
        qvIgLink.setAttribute("data-ig-text", card.getAttribute("data-ig-text") || "");
        var igUrl = card.getAttribute("data-ig-link");
        if (igUrl) { qvIgLink.setAttribute("href", igUrl); }
      }

      qvBackdrop.hidden = false;
      qvPanel.hidden = false;
      requestAnimationFrame(function () {
        qvBackdrop.classList.add("is-open");
        qvPanel.classList.add("is-open");
      });
      document.body.classList.add("mobile-menu-open");
      if (qvClose) { qvClose.focus(); }
    }

    function closeQuickView() {
      qvBackdrop.classList.remove("is-open");
      qvPanel.classList.remove("is-open");
      document.body.classList.remove("mobile-menu-open");
      window.setTimeout(function () {
        qvBackdrop.hidden = true;
        qvPanel.hidden = true;
      }, reduceMotion ? 0 : 320);
      if (qvLastTrigger) { qvLastTrigger.focus(); }
    }

    document.addEventListener("click", function (e) {
      var trigger = e.target.closest && e.target.closest("[data-quickview-trigger]");
      if (trigger) {
        e.preventDefault();
        e.stopPropagation();
        openQuickView(trigger);
      }
    });
    if (qvClose) { qvClose.addEventListener("click", closeQuickView); }
    qvBackdrop.addEventListener("click", closeQuickView);
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && qvPanel.classList.contains("is-open")) { closeQuickView(); }
    });
  }

  /* ------------------------------------------------------------------
     Instagram DM Enquiry Helper:
     Copies the product enquiry message to the user's clipboard and
     displays a clean floating toast, making it effortless to paste
     into Instagram DM upon opening.
     ------------------------------------------------------------------ */
  var igToast = null;
  var igToastTimer = null;

  function showIgToast(msg) {
    if (!igToast) {
      igToast = document.createElement("div");
      igToast.className = "ig-copy-toast";
      igToast.setAttribute("role", "status");
      igToast.setAttribute("aria-live", "polite");
      document.body.appendChild(igToast);
    }
    igToast.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg><span>' + (msg || "Enquiry message copied! Paste into Instagram DM") + '</span>';
    igToast.classList.add("is-visible");
    if (igToastTimer) { clearTimeout(igToastTimer); }
    igToastTimer = setTimeout(function () {
      igToast.classList.remove("is-visible");
    }, 3200);
  }

  document.addEventListener("click", function (e) {
    var igBtn = e.target.closest && e.target.closest("[data-ig-enquire]");
    if (!igBtn) { return; }
    var text = igBtn.getAttribute("data-ig-text");
    if (!text) {
      var name = igBtn.getAttribute("data-product-name");
      if (name) {
        text = "Hi Soleslay, I am interested in " + name + ". Is it available in stock?";
      } else {
        text = "Hi Soleslay, I would like to know more about your footwear collection.";
      }
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () {
        showIgToast("Enquiry copied to clipboard! Paste in Instagram DM");
      }).catch(function () {
        showIgToast("Opening Instagram DM...");
      });
    } else {
      showIgToast("Opening Instagram DM...");
    }
  });

  /* ------------------------------------------------------------------
     5. Product gallery crossfade note: the actual crossfade swap logic
     lives inside showImage() in the gallery block above (edited to use
     the two stacked .gallery-crossfade-img layers instead of a hard
     src swap) — kept there rather than duplicated here so there's a
     single source of truth for gallery state/index tracking.
     ------------------------------------------------------------------ */

  /* ------------------------------------------------------------------
     6. Sticky mobile buy bar: hidden while the page's own Enquiry
     button is on screen, appears once it scrolls out of view so
     there's never a duplicate visible CTA at the same time.
     ------------------------------------------------------------------ */
  var stickyBar = document.getElementById("sticky-buy-bar");
  var mainEnquiryBtn = document.querySelector("[data-enquiry-btn]");
  if (stickyBar && mainEnquiryBtn && "IntersectionObserver" in window) {
    document.body.classList.add("has-sticky-buy-bar");
    var stickyObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        var scrolledPast = !entry.isIntersecting && entry.boundingClientRect.top < 0;
        stickyBar.classList.toggle("is-visible", scrolledPast);
      });
    }, { threshold: 0 });
    stickyObserver.observe(mainEnquiryBtn);
  }

  /* ------------------------------------------------------------------
     7. Hero image parallax on scroll (subtle, desktop + mobile alike):
     the hero product image drifts a few px slower than the page as
     you scroll past it, for a light sense of depth.
     ------------------------------------------------------------------ */
  var heroImageWrap = document.querySelector(".hero-product-image-wrap");
  var heroSection = document.getElementById("hero");
  if (heroImageWrap && heroSection && !reduceMotion) {
    var ticking = false;
    function updateParallax() {
      var rect = heroSection.getBoundingClientRect();
      var progress = Math.min(Math.max(-rect.top / (rect.height || 1), 0), 1);
      heroImageWrap.style.transform = "translateY(" + (progress * 28) + "px)";
      ticking = false;
    }
    window.addEventListener("scroll", function () {
      if (!ticking) {
        window.requestAnimationFrame(updateParallax);
        ticking = true;
      }
    }, { passive: true });
    updateParallax();
  }

  /* ------------------------------------------------------------------
     8. Floating "trending now" badge: cycles through a short list of
     recent arrivals every few seconds with a quick crossfade. Skipped
     under reduced motion (text just stays on the first item).
     ------------------------------------------------------------------ */
  var trendBadge = document.querySelector("[data-trend-badge]");
  if (trendBadge && !reduceMotion) {
    var trendText = trendBadge.querySelector("[data-trend-text]");
    var trendItems = [];
    try { trendItems = JSON.parse(trendBadge.getAttribute("data-trend-items") || "[]"); } catch (err) { trendItems = []; }
    if (trendText && trendItems.length > 1) {
      var trendIndex = 0;
      window.setInterval(function () {
        trendIndex = (trendIndex + 1) % trendItems.length;
        trendText.classList.add("is-swapping");
        window.setTimeout(function () {
          trendText.textContent = "Trending: " + trendItems[trendIndex];
          trendText.classList.remove("is-swapping");
        }, 250);
      }, 4000);
    }
  }

  /* ------------------------------------------------------------------
     9. Luxury 3D Sneaker Horizon Showcase for New Arrivals
     ------------------------------------------------------------------ */
  var horizonShowcase = document.querySelector("[data-horizon-showcase]");
  if (horizonShowcase) {
    (function initHorizonShowcase() {
      var viewport = horizonShowcase.querySelector("[data-horizon-viewport]");
      var track = horizonShowcase.querySelector("[data-horizon-track]");
      var cards = Array.prototype.slice.call(horizonShowcase.querySelectorAll("[data-horizon-card]"));
      var prevBtn = horizonShowcase.querySelector("[data-horizon-prev]");
      var nextBtn = horizonShowcase.querySelector("[data-horizon-next]");
      var pagination = horizonShowcase.querySelector("[data-horizon-pagination]");
      var currentCounter = horizonShowcase.querySelector("[data-horizon-current]");
      var totalCounter = horizonShowcase.querySelector("[data-horizon-total]");

      if (!viewport || !track || cards.length === 0) { return; }

      var numCards = cards.length;
      var currentIndex = 0;
      var targetIndex = 0;
      var lastSnappedIndex = 0;
      var isDragging = false;
      var startX = 0;
      var lastX = 0;
      var lastMoveTime = 0;
      var velocityX = 0;
      var hasMoved = false;
      var isHovered = false;
      var autoTimer = null;
      var dots = [];

      // Setup total counter
      if (totalCounter) {
        totalCounter.textContent = (numCards < 10 ? "0" : "") + numCards;
      }

      // Generate dynamic pagination dots
      if (pagination) {
        pagination.innerHTML = "";
        for (var d = 0; d < numCards; d++) {
          var dot = document.createElement("button");
          dot.type = "button";
          dot.className = "horizon-dot" + (d === 0 ? " is-active" : "");
          dot.setAttribute("role", "tab");
          dot.setAttribute("aria-label", "Go to sneaker " + (d + 1) + " of " + numCards);
          dot.setAttribute("data-dot-index", d);
          (function (idx) {
            dot.addEventListener("click", function (e) {
              e.preventDefault();
              goToCard(idx);
            });
          })(d);
          pagination.appendChild(dot);
          dots.push(dot);
        }
      }

      function getNormalizedIndex(val) {
        var mod = val % numCards;
        return mod < 0 ? mod + numCards : mod;
      }

      function goToCard(targetIdx) {
        var normCur = getNormalizedIndex(Math.round(targetIndex));
        var diff = targetIdx - normCur;
        if (diff > numCards / 2) { diff -= numCards; }
        if (diff < -numCards / 2) { diff += numCards; }
        targetIndex = Math.round(targetIndex) + diff;
        pauseAutoScroll(HOLD_DURATION_MS);
      }

      function updatePagination(activeIndex) {
        dots.forEach(function (dot, idx) {
          dot.classList.toggle("is-active", idx === activeIndex);
          dot.setAttribute("aria-selected", idx === activeIndex ? "true" : "false");
        });
        if (currentCounter) {
          var displayNum = activeIndex + 1;
          currentCounter.textContent = (displayNum < 10 ? "0" : "") + displayNum;
        }
      }

      function renderFrame() {
        var isMobile = window.innerWidth <= 768;
        var spacing = isMobile ? 195 : 275;
        var activeSnap = getNormalizedIndex(Math.round(currentIndex));

        if (activeSnap !== lastSnappedIndex) {
          lastSnappedIndex = activeSnap;
          updatePagination(activeSnap);
        }

        cards.forEach(function (card, i) {
          var diff = (i - currentIndex) % numCards;
          if (diff > numCards / 2) { diff -= numCards; }
          if (diff < -numCards / 2) { diff += numCards; }

          var absDiff = Math.abs(diff);

          if (absDiff > 2.8) {
            card.style.opacity = "0";
            card.style.visibility = "hidden";
            card.style.pointerEvents = "none";
            card.classList.remove("is-active");
            return;
          }

          card.style.visibility = "visible";

          // Calculate 3D coverflow transforms (Max scale 1.0 preserves 100% sharp text)
          var translateX = diff * spacing;
          var translateZ = -absDiff * (isMobile ? 55 : 80);
          var rotateY = -diff * 22;
          if (rotateY > 36) { rotateY = 36; }
          if (rotateY < -36) { rotateY = -36; }

          var scale = Math.max(0.72, 1.0 - absDiff * 0.15);
          var opacity = Math.max(0, 1 - absDiff * 0.28);
          var zIndex = Math.round(50 - absDiff * 10);

          card.style.transform = "translate3d(" + translateX.toFixed(1) + "px, 0, " + translateZ.toFixed(1) + "px) rotateY(" + rotateY.toFixed(1) + "deg) scale(" + scale.toFixed(3) + ")";
          card.style.opacity = opacity.toFixed(2);
          card.style.zIndex = zIndex;

          if (absDiff < 0.5) {
            card.classList.add("is-active");
            card.style.pointerEvents = "auto";
          } else {
            card.classList.remove("is-active");
            card.style.pointerEvents = "auto";
          }
        });
      }

      // 2-Second Hold & Step Auto-Scroll Engine
      var isAutoScrolling = !reduceMotion;
      var HOLD_DURATION_MS = 2000; // Hold for 2 seconds on every card
      var holdElapsed = 0;
      var pauseUntil = performance.now() + HOLD_DURATION_MS;
      var lastFrameTime = performance.now();
      var lastRenderedIndex = -999;
      var isIntersecting = true;

      // Only auto-advance when showcase is visible in viewport
      if ("IntersectionObserver" in window) {
        var observer = new IntersectionObserver(function (entries) {
          entries.forEach(function (entry) {
            isIntersecting = entry.isIntersecting;
            if (isIntersecting) {
              lastFrameTime = performance.now();
              pauseAutoScroll(HOLD_DURATION_MS);
            }
          });
        }, { threshold: 0.15 });
        observer.observe(horizonShowcase);
      }

      function pauseAutoScroll(durationMs) {
        var delay = durationMs !== undefined ? durationMs : HOLD_DURATION_MS;
        pauseUntil = performance.now() + delay;
        holdElapsed = 0;
      }

      function animate(now) {
        if (!now) { now = performance.now(); }
        var dt = (now - lastFrameTime) / 1000;
        lastFrameTime = now;
        if (dt > 0.1 || dt <= 0) { dt = 0.016; }

        if (!isDragging) {
          var dist = Math.abs(targetIndex - currentIndex);
          if (dist < 0.004) {
            // Card is resting dead center
            currentIndex = targetIndex;
            var canAuto = isAutoScrolling && !isHovered && !reduceMotion && isIntersecting && (now >= pauseUntil);
            if (canAuto) {
              holdElapsed += dt * 1000;
              if (holdElapsed >= HOLD_DURATION_MS) {
                targetIndex = Math.round(targetIndex) + 1;
                holdElapsed = 0;
              }
            } else {
              holdElapsed = 0;
            }
          } else {
            // Smoothly glide into target card
            var ease = Math.min(1, 0.12 * (dt / 0.016));
            currentIndex += (targetIndex - currentIndex) * ease;
            holdElapsed = 0;
          }
        } else {
          var dragEase = Math.min(1, 0.35 * (dt / 0.016));
          currentIndex += (targetIndex - currentIndex) * dragEase;
          holdElapsed = 0;
        }

        // Only touch DOM styles when coordinates have actually moved
        if (Math.abs(currentIndex - lastRenderedIndex) > 0.0001) {
          lastRenderedIndex = currentIndex;
          renderFrame();
        }

        requestAnimationFrame(animate);
      }

      requestAnimationFrame(animate);

      // Pointer drag interaction
      viewport.addEventListener("pointerdown", function (e) {
        if (e.pointerType === "mouse" && e.button !== 0) { return; }
        // Don't drag if clicking buttons or links
        if (e.target.closest("a") || e.target.closest("button")) { return; }
        isDragging = true;
        startX = e.clientX;
        lastX = e.clientX;
        lastMoveTime = performance.now();
        velocityX = 0;
        hasMoved = false;
        viewport.classList.add("is-dragging");
        try { viewport.setPointerCapture(e.pointerId); } catch (err) {}
        pauseAutoScroll(HOLD_DURATION_MS);
      });

      viewport.addEventListener("pointermove", function (e) {
        if (!isDragging) { return; }
        var dx = e.clientX - lastX;
        var now = performance.now();
        var dt = Math.max(1, now - lastMoveTime);
        velocityX = dx / dt;
        lastX = e.clientX;
        lastMoveTime = now;

        if (Math.abs(e.clientX - startX) > 6) {
          hasMoved = true;
        }

        var sensitivity = window.innerWidth <= 768 ? 0.0048 : 0.0034;
        targetIndex -= dx * sensitivity;
      });

      function onPointerEnd(e) {
        if (!isDragging) { return; }
        isDragging = false;
        viewport.classList.remove("is-dragging");
        try { viewport.releasePointerCapture(e.pointerId); } catch (err) {}

        // Add momentum flick
        var flick = velocityX * 120;
        if (Math.abs(flick) > 0.4) {
          targetIndex -= flick * 0.005;
        }

        targetIndex = Math.round(targetIndex);
        pauseAutoScroll(HOLD_DURATION_MS);
      }

      viewport.addEventListener("pointerup", onPointerEnd);
      viewport.addEventListener("pointercancel", onPointerEnd);

      // Hover handling: pause auto scroll when inspecting
      horizonShowcase.addEventListener("mouseenter", function () {
        isHovered = true;
      });
      horizonShowcase.addEventListener("mouseleave", function () {
        isHovered = false;
        pauseAutoScroll(HOLD_DURATION_MS);
      });
      horizonShowcase.addEventListener("pointerenter", function (e) {
        if (e.pointerType === "mouse") {
          isHovered = true;
        }
      });
      horizonShowcase.addEventListener("pointerleave", function (e) {
        if (e.pointerType === "mouse") {
          isHovered = false;
          pauseAutoScroll(HOLD_DURATION_MS);
        }
      });

      // Card click handling
      cards.forEach(function (card, index) {
        card.addEventListener("click", function (e) {
          // If user dragged, don't trigger click action
          if (hasMoved) {
            e.preventDefault();
            return;
          }

          // If clicked a button or link inside the card, allow natural click
          if (e.target.closest("a") || e.target.closest("button")) {
            return;
          }

          var diff = (index - currentIndex) % numCards;
          if (diff > numCards / 2) { diff -= numCards; }
          if (diff < -numCards / 2) { diff += numCards; }

          if (Math.abs(diff) >= 0.5) {
            // Clicked a flanking card: bring to center
            e.preventDefault();
            targetIndex = Math.round(currentIndex + diff);
            pauseAutoScroll(HOLD_DURATION_MS);
          } else {
            // Clicked active front card: navigate to detail page
            var url = card.getAttribute("data-url");
            if (url) {
              window.location.href = url;
            }
          }
        });
      });

      // Frame Navigation Buttons
      if (prevBtn) {
        prevBtn.addEventListener("click", function (e) {
          e.preventDefault();
          targetIndex = Math.round(targetIndex) - 1;
          pauseAutoScroll(HOLD_DURATION_MS);
        });
      }

      if (nextBtn) {
        nextBtn.addEventListener("click", function (e) {
          e.preventDefault();
          targetIndex = Math.round(targetIndex) + 1;
          pauseAutoScroll(HOLD_DURATION_MS);
        });
      }

      // Keyboard arrow navigation
      viewport.addEventListener("keydown", function (e) {
        if (e.key === "ArrowLeft") {
          e.preventDefault();
          targetIndex = Math.round(targetIndex) - 1;
          pauseAutoScroll(HOLD_DURATION_MS);
        } else if (e.key === "ArrowRight") {
          e.preventDefault();
          targetIndex = Math.round(targetIndex) + 1;
          pauseAutoScroll(HOLD_DURATION_MS);
        }
      });

      // Mouse wheel horizontal scrubbing on showcase
      viewport.addEventListener("wheel", function (e) {
        var delta = Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : (e.shiftKey ? e.deltaY : 0);
        if (Math.abs(delta) > 15) {
          e.preventDefault();
          targetIndex += delta > 0 ? 0.35 : -0.35;
          targetIndex = Math.round(targetIndex);
          pauseAutoScroll(HOLD_DURATION_MS);
        }
      }, { passive: false });

      // Page visibility change: pause when tab is inactive
      document.addEventListener("visibilitychange", function () {
        if (document.hidden) {
          isAutoScrolling = false;
        } else {
          lastFrameTime = performance.now();
          isAutoScrolling = !reduceMotion;
          pauseAutoScroll(HOLD_DURATION_MS);
        }
      });

      // Window resize re-render
      window.addEventListener("resize", function () {
        renderFrame();
      });
    })();
  }

  /* ------------------------------------------------------------------
     Footer: VIP Sneaker Drop Club Submission & Live Store Status
     ------------------------------------------------------------------ */
  window.handleDropClubSubmit = function (form) {
    if (!form) { return; }
    var input = form.querySelector('input[name="vip_contact"]');
    var val = input ? input.value.trim() : "";
    if (!val) { return; }

    showIgToast("🔥 You're on the Soleslay VIP drop list! Early access unlocked.");
    if (input) {
      input.value = "";
      input.blur();
    }
  };

  function updateLiveStoreStatus() {
    var statusEl = document.getElementById("footer-store-status");
    if (!statusEl) { return; }

    try {
      var now = new Date();
      var istOffset = 5.5 * 60 * 60 * 1000;
      var istTime = new Date(now.getTime() + (now.getTimezoneOffset() * 60000) + istOffset);
      var hours = istTime.getHours();
      var minutes = istTime.getMinutes();
      var totalMinutes = hours * 60 + minutes;

      var openMinutes = 10 * 60; // 10:00 AM
      var closeMinutes = 22 * 60; // 10:00 PM

      var stateEl = statusEl.querySelector(".live-status-state");
      var timeEl = statusEl.querySelector(".live-status-time");
      var radarEl = statusEl.querySelector(".live-status-radar");

      if (totalMinutes >= openMinutes && totalMinutes < closeMinutes) {
        if (stateEl) {
          stateEl.textContent = "OPEN NOW";
          stateEl.style.color = "#34D399";
        }
        if (timeEl) { timeEl.textContent = "Closes at 10:00 PM IST"; }
        if (radarEl) { radarEl.style.display = "block"; }
      } else {
        if (stateEl) {
          stateEl.textContent = "STORE CLOSED";
          stateEl.style.color = "#94A3B8";
        }
        if (timeEl) { timeEl.textContent = "Opens tomorrow at 10:00 AM IST"; }
        if (radarEl) { radarEl.style.display = "none"; }
      }
    } catch (e) {}
  }
  updateLiveStoreStatus();

  var backToTop = document.getElementById("footer-back-to-top");
  if (backToTop) {
    backToTop.addEventListener("click", function (e) {
      e.preventDefault();
      window.scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" });
    });
  }
})();

