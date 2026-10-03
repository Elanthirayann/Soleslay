/**
 * React Bits - The Tactile Studio & Hero 3D Parallax
 *
 * Implements native 60fps micro-physics for:
 * 1. SpotlightCard (dynamic cursor spotlight and border light catcher)
 * 2. MagneticButton (elastic spring cursor attraction and recoil)
 * 3. HeroShoeParallax (3D perspective floating shoe tilt on cursor move)
 * 4. ShinyText (specular metallic light sweep)
 */
(function () {
  "use strict";

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var isTouchOnly = window.matchMedia("(pointer: coarse) and (hover: none)").matches;

  /* =========================================================================
     1. SpotlightCard Component
     ========================================================================= */
  function initSpotlightCards() {
    var cards = document.querySelectorAll("[data-spotlight-card], .product-card");
    if (!cards.length) { return; }

    cards.forEach(function (card) {
      if (card.__spotlightInitialized) { return; }
      card.__spotlightInitialized = true;

      // Add base class if not present
      card.classList.add("spotlight-card");

      if (reduceMotion || isTouchOnly) { return; }

      card.addEventListener("pointermove", function (e) {
        var rect = card.getBoundingClientRect();
        if (!rect.width || !rect.height) { return; }

        var x = e.clientX - rect.left;
        var y = e.clientY - rect.top;

        card.style.setProperty("--mouse-x", x.toFixed(1) + "px");
        card.style.setProperty("--mouse-y", y.toFixed(1) + "px");
        card.classList.add("is-spotlight-active");
      });

      card.addEventListener("pointerleave", function () {
        card.classList.remove("is-spotlight-active");
      });
    });
  }

  /* =========================================================================
     2. MagneticButton Component
     ========================================================================= */
  function initMagneticButtons() {
    var btns = document.querySelectorAll("[data-magnetic], .whatsapp-fab, .btn-hero-whatsapp");
    if (!btns.length || reduceMotion || isTouchOnly) { return; }

    btns.forEach(function (btn) {
      if (btn.__magneticInitialized) { return; }
      btn.__magneticInitialized = true;

      btn.classList.add("magnetic-btn");

      var currentX = 0;
      var currentY = 0;
      var targetX = 0;
      var targetY = 0;
      var rafId = null;
      var isHovered = false;

      var maxDistance = parseFloat(btn.getAttribute("data-magnetic-distance")) || 14; // max px displacement
      var pullStrength = parseFloat(btn.getAttribute("data-magnetic-strength")) || 0.35;

      function update() {
        var ease = isHovered ? 0.22 : 0.12;
        currentX += (targetX - currentX) * ease;
        currentY += (targetY - currentY) * ease;

        btn.style.transform = "translate3d(" + currentX.toFixed(2) + "px, " + currentY.toFixed(2) + "px, 0)";

        var diff = Math.abs(targetX - currentX) + Math.abs(targetY - currentY);
        if (diff > 0.05 || isHovered) {
          rafId = requestAnimationFrame(update);
        } else {
          btn.style.transform = "translate3d(0, 0, 0)";
          rafId = null;
        }
      }

      btn.addEventListener("pointerenter", function () {
        isHovered = true;
        if (!rafId) { rafId = requestAnimationFrame(update); }
      });

      btn.addEventListener("pointermove", function (e) {
        var rect = btn.getBoundingClientRect();
        if (!rect.width || !rect.height) { return; }

        var centerX = rect.left + rect.width / 2;
        var centerY = rect.top + rect.height / 2;

        var deltaX = (e.clientX - centerX) * pullStrength;
        var deltaY = (e.clientY - centerY) * pullStrength;

        // Clamp to max distance
        var dist = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
        if (dist > maxDistance) {
          var ratio = maxDistance / dist;
          deltaX *= ratio;
          deltaY *= ratio;
        }

        targetX = deltaX;
        targetY = deltaY;

        if (!rafId) { rafId = requestAnimationFrame(update); }
      });

      btn.addEventListener("pointerleave", function () {
        isHovered = false;
        targetX = 0;
        targetY = 0;
        if (!rafId) { rafId = requestAnimationFrame(update); }
      });
    });
  }

  /* =========================================================================
     3. HeroShoeParallax (Idea 3: 3D Shoe Tilt Suspended in Air)
     ========================================================================= */
  function initHeroShoeParallax() {
    var heroSection = document.querySelector("#hero, [data-hero-section]");
    var stage = document.querySelector("[data-shoe-stage]");
    if (!heroSection || !stage || reduceMotion || isTouchOnly) { return; }

    var canvas = stage.querySelector("[data-shoe-canvas]");
    var fallback = stage.querySelector("[data-shoe-fallback]");
    if (!canvas && !fallback) { return; }

    // Ensure stage has 3D perspective setup
    stage.classList.add("hero-parallax-stage");

    var currentRotX = 0;
    var currentRotY = 0;
    var currentTransX = 0;
    var currentTransY = 0;
    var currentScale = 1;

    var targetRotX = 0;
    var targetRotY = 0;
    var targetTransX = 0;
    var targetTransY = 0;
    var targetScale = 1;

    var rafId = null;
    var isInside = false;

    // Maximum tilt angles and translations
    var maxPitch = 12; // deg (X axis)
    var maxYaw = 16;   // deg (Y axis)
    var maxTrans = 14; // px translation

    function updateShoeTransform() {
      var ease = isInside ? 0.14 : 0.08;
      currentRotX += (targetRotX - currentRotX) * ease;
      currentRotY += (targetRotY - currentRotY) * ease;
      currentTransX += (targetTransX - currentTransX) * ease;
      currentTransY += (targetTransY - currentTransY) * ease;
      currentScale += (targetScale - currentScale) * ease;

      var transformStyle =
        "perspective(1200px) rotateX(" +
        currentRotX.toFixed(2) +
        "deg) rotateY(" +
        currentRotY.toFixed(2) +
        "deg) translate3d(" +
        currentTransX.toFixed(2) +
        "px, " +
        currentTransY.toFixed(2) +
        "px, 20px) scale(" +
        currentScale.toFixed(3) +
        ")";

      if (canvas) { canvas.style.transform = transformStyle; }
      if (fallback) { fallback.style.transform = transformStyle; }

      // Dynamic shadow displacement underneath
      var shadow = stage.querySelector(".hero-shoe-parallax-shadow");
      if (shadow) {
        var shadowX = (-currentTransX * 0.7).toFixed(1);
        var shadowY = (-currentTransY * 0.4).toFixed(1);
        var shadowScale = (1 + (currentRotX / maxPitch) * 0.06).toFixed(3);
        shadow.style.transform = "translateX(-50%) translate3d(" + shadowX + "px, " + shadowY + "px, 0) scale(" + shadowScale + ")";
      }

      var delta =
        Math.abs(targetRotX - currentRotX) +
        Math.abs(targetRotY - currentRotY) +
        Math.abs(targetTransX - currentTransX) +
        Math.abs(targetTransY - currentTransY);

      if (delta > 0.02 || isInside) {
        rafId = requestAnimationFrame(updateShoeTransform);
      } else {
        var resetStyle = "perspective(1200px) rotateX(0deg) rotateY(0deg) translate3d(0, 0, 0) scale(1)";
        if (canvas) { canvas.style.transform = resetStyle; }
        if (fallback) { fallback.style.transform = resetStyle; }
        if (shadow) { shadow.style.transform = "translateX(-50%) translate3d(0, 0, 0) scale(1)"; }
        rafId = null;
      }
    }

    function onPointerMove(e) {
      // Check if mouse is within hero bounds
      var rect = heroSection.getBoundingClientRect();
      if (!rect.width || !rect.height) { return; }

      // Also compute relative to stage for tighter reaction near the shoe
      var stageRect = stage.getBoundingClientRect();
      var inStage = (
        e.clientX >= stageRect.left &&
        e.clientX <= stageRect.right &&
        e.clientY >= stageRect.top &&
        e.clientY <= stageRect.bottom
      );

      var referenceRect = inStage ? stageRect : rect;
      var relX = (e.clientX - referenceRect.left) / referenceRect.width; // 0 to 1
      var relY = (e.clientY - referenceRect.top) / referenceRect.height; // 0 to 1

      var normX = (relX - 0.5) * 2; // -1 to 1
      var normY = (relY - 0.5) * 2; // -1 to 1

      // Pitch (tilt up/down) & Yaw (turn left/right)
      targetRotX = -normY * maxPitch;
      targetRotY = normX * maxYaw;
      targetTransX = normX * maxTrans;
      targetTransY = normY * (maxTrans * 0.8);
      targetScale = inStage ? 1.04 : 1.015;

      isInside = true;
      if (!rafId) {
        rafId = requestAnimationFrame(updateShoeTransform);
      }
    }

    function onPointerLeave() {
      isInside = false;
      targetRotX = 0;
      targetRotY = 0;
      targetTransX = 0;
      targetTransY = 0;
      targetScale = 1;
      if (!rafId) {
        rafId = requestAnimationFrame(updateShoeTransform);
      }
    }

    heroSection.addEventListener("pointermove", onPointerMove, { passive: true });
    heroSection.addEventListener("pointerleave", onPointerLeave);
  }

  /* =========================================================================
     4. ShinyText Component
     ========================================================================= */
  function initShinyText() {
    var targets = document.querySelectorAll(".hero-title-row--highlight");
    targets.forEach(function (el) {
      el.classList.add("shiny-text");
    });
  }

  /* =========================================================================
     5. Hero Volumetric Smoke Bomb & Rolling Cloud Engine (Hero Section Only)
     ========================================================================= */
  function initHeroSmokeCursor() {
    var hero = document.querySelector("#hero, [data-hero-section]");
    if (!hero || reduceMotion || isTouchOnly) { return; }

    var viewport = hero.querySelector(".hero-sticky-viewport") || hero;
    var canvas = viewport.querySelector("[data-hero-smoke-canvas]");
    if (!canvas) {
      canvas = document.createElement("canvas");
      canvas.className = "hero-smoke-canvas";
      canvas.setAttribute("data-hero-smoke-canvas", "");
      canvas.setAttribute("aria-hidden", "true");
      viewport.insertBefore(canvas, viewport.firstChild);
    }

    var ctx = canvas.getContext("2d");
    if (!ctx) { return; }

    var width = 0;
    var height = 0;
    var dpr = 1;
    var particles = [];
    var animId = null;
    var lastX = null;
    var lastY = null;

    function resize() {
      var rect = viewport.getBoundingClientRect();
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = rect.width;
      height = rect.height;
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      canvas.style.width = width + "px";
      canvas.style.height = height + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    resize();
    window.addEventListener("resize", resize);

    // Pre-render 5 cinematic, ultra-smooth volumetric smoke bomb puff sprites (320x320)
    var smokeSprites = [];
    var spriteSize = 320;
    var half = spriteSize / 2;

    for (var s = 0; s < 5; s++) {
      var spCanvas = document.createElement("canvas");
      spCanvas.width = spriteSize;
      spCanvas.height = spriteSize;
      var spCtx = spCanvas.getContext("2d");

      // Multi-layered cumulus cauliflower lobes
      var numLobes = 12;
      for (var i = 0; i < numLobes; i++) {
        var angle = (i / numLobes) * Math.PI * 2 + (s * 0.5);
        var dist = 48 + (i % 3) * 20;
        var lx = half + Math.cos(angle) * dist;
        var ly = half + Math.sin(angle) * dist;
        var r = 78 + ((i + s) % 4) * 16;

        var grad = spCtx.createRadialGradient(lx, ly, 0, lx, ly, r);
        grad.addColorStop(0, "rgba(85, 100, 120, 0.22)");
        grad.addColorStop(0.35, "rgba(125, 140, 160, 0.14)");
        grad.addColorStop(0.70, "rgba(180, 195, 215, 0.05)");
        grad.addColorStop(1, "rgba(255, 255, 255, 0)");

        spCtx.fillStyle = grad;
        spCtx.beginPath();
        spCtx.arc(lx, ly, r, 0, Math.PI * 2);
        spCtx.fill();
      }

      // Dense, rich volumetric center
      var coreGrad = spCtx.createRadialGradient(half, half, 0, half, half, 95);
      coreGrad.addColorStop(0, "rgba(60, 75, 95, 0.28)");
      coreGrad.addColorStop(0.40, "rgba(85, 100, 120, 0.18)");
      coreGrad.addColorStop(0.75, "rgba(135, 150, 170, 0.05)");
      coreGrad.addColorStop(1, "rgba(255, 255, 255, 0)");
      spCtx.fillStyle = coreGrad;
      spCtx.beginPath();
      spCtx.arc(half, half, 95, 0, Math.PI * 2);
      spCtx.fill();

      smokeSprites.push(spCanvas);
    }

    // BIG SMOKE BOMB Detonation (on click / touch / fast strike)
    function detonateSmokeBomb(x, y, count, power) {
      var n = count || 20;
      var pow = power || 1.0;
      for (var i = 0; i < n; i++) {
        var angle = (i / n) * Math.PI * 2 + (Math.random() - 0.5) * 0.4;
        var speed = (Math.random() * 4.2 + 2.4) * pow;
        var sprite = smokeSprites[Math.floor(Math.random() * smokeSprites.length)];

        particles.push({
          x: x + (Math.random() - 0.5) * 30,
          y: y + (Math.random() - 0.5) * 30,
          vx: Math.cos(angle) * speed,
          vy: Math.sin(angle) * speed - 0.7, // buoyant upward drift
          size: 110 + Math.random() * 50,    // starts BIG (110 - 160px)
          maxSize: 340 + Math.random() * 110,// expands to massive 340 - 450px!
          growth: 2.2 + Math.random() * 1.6, // rapid billowing expansion
          alpha: 0.42 + Math.random() * 0.14,
          decay: 0.0035 + Math.random() * 0.0014, // long cinematic hang time
          rotation: Math.random() * Math.PI * 2,
          vRot: (Math.random() - 0.5) * 0.014,
          sprite: sprite
        });
      }

      if (!animId) {
        animId = requestAnimationFrame(render);
      }
    }

    // Continuous big rolling smoke bomb trail following cursor
    function addTrailPuff(x, y, vx, vy, dist) {
      var count = Math.min(4, Math.max(1, Math.floor(dist / 6)));
      for (var i = 0; i < count; i++) {
        var sprite = smokeSprites[Math.floor(Math.random() * smokeSprites.length)];
        var spread = (Math.random() - 0.5) * 22;
        particles.push({
          x: x + spread,
          y: y + spread,
          vx: vx * 0.22 + (Math.random() - 0.5) * 1.4,
          vy: vy * 0.22 - Math.random() * 0.7 - 0.4,
          size: 105 + Math.random() * 45,
          maxSize: 280 + Math.random() * 90,
          growth: 1.8 + Math.random() * 1.1,
          alpha: 0.36 + Math.random() * 0.12,
          decay: 0.0040 + Math.random() * 0.0014,
          rotation: Math.random() * Math.PI * 2,
          vRot: (Math.random() - 0.5) * 0.016,
          sprite: sprite
        });
      }

      if (!animId) {
        animId = requestAnimationFrame(render);
      }
    }

    function render() {
      ctx.clearRect(0, 0, width, height);

      for (var i = particles.length - 1; i >= 0; i--) {
        var p = particles[i];
        p.x += p.vx;
        p.y += p.vy;
        p.vx *= 0.972; // atmospheric friction
        p.vy = p.vy * 0.972 - 0.08; // thermal buoyancy lift
        p.size = Math.min(p.maxSize, p.size + p.growth);
        p.alpha -= p.decay;
        p.rotation += p.vRot;

        if (p.alpha <= 0.004) {
          particles.splice(i, 1);
          continue;
        }

        ctx.save();
        ctx.globalAlpha = p.alpha;
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rotation);
        ctx.drawImage(p.sprite, -p.size / 2, -p.size / 2, p.size, p.size);
        ctx.restore();
      }

      if (particles.length > 0) {
        animId = requestAnimationFrame(render);
      } else {
        animId = null;
        ctx.clearRect(0, 0, width, height);
      }
    }

    // Touch / Click detonate Smoke Bomb
    hero.addEventListener("pointerdown", function (e) {
      var rect = viewport.getBoundingClientRect();
      var x = e.clientX - rect.left;
      var y = e.clientY - rect.top;
      if (x >= 0 && y >= 0 && x <= rect.width && y <= rect.height) {
        detonateSmokeBomb(x, y, 22, 1.3);
      }
    });

    hero.addEventListener("pointermove", function (e) {
      var rect = viewport.getBoundingClientRect();
      var x = e.clientX - rect.left;
      var y = e.clientY - rect.top;

      if (x < 0 || y < 0 || x > rect.width || y > rect.height) {
        lastX = null;
        lastY = null;
        return;
      }

      if (lastX !== null && lastY !== null) {
        var dist = Math.hypot(x - lastX, y - lastY);
        if (dist > 4) {
          var steps = Math.min(8, Math.ceil(dist / 14));
          for (var s = 1; s <= steps; s++) {
            var t = s / steps;
            var ix = lastX + (x - lastX) * t;
            var iy = lastY + (y - lastY) * t;
            var vx = (x - lastX) / steps;
            var vy = (y - lastY) / steps;
            addTrailPuff(ix, iy, vx, vy, dist);
          }
        }
      } else {
        // Initial touch/enter burst
        detonateSmokeBomb(x, y, 10, 0.9);
      }

      lastX = x;
      lastY = y;
    }, { passive: true });

    hero.addEventListener("pointerleave", function () {
      lastX = null;
      lastY = null;
    });

    // Expose for external access
    window.__heroSmokeBomb = detonateSmokeBomb;
  }

  /* =========================================================================
     Master Initialization
     ========================================================================= */
  function initAll() {
    initSpotlightCards();
    initMagneticButtons();
    initHeroShoeParallax();
    initShinyText();
    initHeroSmokeCursor();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAll);
  } else {
    initAll();
  }

  // Export globally for dynamically rendered components
  window.initReactBits = initAll;
  window.initSpotlightCards = initSpotlightCards;
  window.initMagneticButtons = initMagneticButtons;
  window.initHeroShoeParallax = initHeroShoeParallax;
  window.initShinyText = initShinyText;
  window.initHeroSmokeCursor = initHeroSmokeCursor;
})();
