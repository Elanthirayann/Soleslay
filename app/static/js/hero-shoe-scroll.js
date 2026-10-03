/*
 * Scroll-driven hero shoe explosion with smooth lerp progress easing.
 *
 * Renders a 50-frame image sequence onto a single <canvas>, mapping
 * scroll position (and touch/drag scrub) to crisp, solid single frames.
 * All frames are preloaded rapidly in parallel and decoded to GPU memory.
 * Progress is interpolated smoothly with requestAnimationFrame lerp easing
 * for a silky, liquid-smooth Apple/Nike product showcase feel without ghosting.
 */
(function () {
  "use strict";

  var stage = document.querySelector("[data-shoe-stage]");
  if (!stage) { return; }

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduceMotion) { return; }

  var track = document.querySelector("[data-hero-scroll-track]");
  var canvas = stage.querySelector("[data-shoe-canvas]");
  var fallbackImg = stage.querySelector("[data-shoe-fallback]");
  var progressFill = stage.querySelector("[data-shoe-progress-fill]");
  if (!track || !canvas || !fallbackImg) { return; }

  var frameBase = stage.getAttribute("data-shoe-frame-base") || "";
  var frameCount = parseInt(stage.getAttribute("data-shoe-frame-count"), 10) || 50;
  var naturalWidth = parseInt(stage.getAttribute("data-shoe-frame-width"), 10) || 1400;
  var naturalHeight = parseInt(stage.getAttribute("data-shoe-frame-height"), 10) || 788;
  if (!frameBase || !frameCount) { return; }

  function frameUrl(n) {
    var num = String(n);
    while (num.length < 3) { num = "0" + num; }
    return frameBase + num + ".webp";
  }

  // ---- Frame cache: array of Image objects, indexed 1..frameCount ----
  var frames = new Array(frameCount + 1);
  var loadedCount = 0;
  var ctx = canvas.getContext("2d", { alpha: true });
  var isReady = false;

  function loadSingleFrame(n, onDone) {
    if (frames[n]) { if (onDone) { onDone(); } return; }
    var img = new Image();
    img.decoding = "async";
    img.onload = function () {
      if (img.decode) {
        img.decode().catch(function () {}).finally(function () {
          frames[n] = img;
          loadedCount++;
          if (onDone) { onDone(); }
        });
      } else {
        frames[n] = img;
        loadedCount++;
        if (onDone) { onDone(); }
      }
    };
    img.onerror = function () {
      if (onDone) { onDone(); }
    };
    img.src = frameUrl(n);
  }

  // Fast concurrent preloader: load priority frames 1..8 first, then rest in parallel
  function preloadAllFrames(onFirstReady) {
    var firstFired = false;
    var PRIORITY = 8;
    var priorityLoaded = 0;

    // Load initial 8 frames with highest priority
    for (var i = 1; i <= Math.min(PRIORITY, frameCount); i++) {
      (function (num) {
        loadSingleFrame(num, function () {
          priorityLoaded++;
          if (!firstFired && frames[1]) {
            firstFired = true;
            onFirstReady();
          }
          if (priorityLoaded >= Math.min(PRIORITY, frameCount)) {
            loadRemainingBatched();
          }
        });
      })(i);
    }
  }

  function loadRemainingBatched() {
    var queue = [];
    for (var i = 9; i <= frameCount; i++) {
      queue.push(i);
    }
    var CONCURRENCY = 8;
    var active = 0;

    function next() {
      if (queue.length === 0) { return; }
      while (active < CONCURRENCY && queue.length > 0) {
        var n = queue.shift();
        active++;
        (function (num) {
          loadSingleFrame(num, function () {
            active--;
            next();
          });
        })(n);
      }
    }
    next();
  }

  // ---- Canvas sizing (device-pixel-ratio aware, object-fit: contain) ----
  var canvasCssW = 0;
  var canvasCssH = 0;

  function sizeCanvas() {
    var rect = stage.getBoundingClientRect();
    var dpr = Math.min(window.devicePixelRatio || 1, 2.5);
    canvasCssW = rect.width;
    canvasCssH = rect.height;
    canvas.width = Math.max(1, Math.round(canvasCssW * dpr));
    canvas.height = Math.max(1, Math.round(canvasCssH * dpr));
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    drawSolidFrame(1 + smoothedProgress * (frameCount - 1));
  }

  // Solid single-frame rendering to eliminate ghosting / double-image artifacts
  function drawSolidFrame(floatIndex) {
    if (!canvasCssW || !canvasCssH) { return; }

    var targetIndex = Math.round(floatIndex);
    if (targetIndex < 1) { targetIndex = 1; }
    if (targetIndex > frameCount) { targetIndex = frameCount; }

    var img = frames[targetIndex];
    if (!img) {
      // Fallback to nearest loaded frame if current isn't ready yet
      for (var d = 1; d < frameCount; d++) {
        if (frames[targetIndex - d]) { img = frames[targetIndex - d]; break; }
        if (frames[targetIndex + d]) { img = frames[targetIndex + d]; break; }
      }
    }
    if (!img) { return; }

    ctx.clearRect(0, 0, canvasCssW, canvasCssH);

    var scale = Math.min(canvasCssW / naturalWidth, canvasCssH / naturalHeight);
    var drawW = naturalWidth * scale;
    var drawH = naturalHeight * scale;
    var offsetX = (canvasCssW - drawW) / 2;
    var offsetY = (canvasCssH - drawH) / 2;

    // Render single frame at 100% opacity - completely crisp and solid
    ctx.globalAlpha = 1.0;
    ctx.drawImage(img, offsetX, offsetY, drawW, drawH);
  }

  // ---- Smooth Progress Easing Engine ----
  var targetProgress = 0;
  var smoothedProgress = 0;
  var isLoopRunning = false;

  function computeProgress() {
    var scrolled = window.scrollY || window.pageYOffset || 0;
    // Completes layer separation across 380px of natural scroll so all 50 layers
    // fully explode into view while the hero section is still right in front of the user.
    var maxScroll = 380;
    var progress = scrolled / maxScroll;
    if (progress < 0) { progress = 0; }
    if (progress > 1) { progress = 1; }
    return progress;
  }

  function renderAtProgress(progress) {
    var floatIdx = 1 + progress * (frameCount - 1);
    drawSolidFrame(floatIdx);

    if (progressFill) {
      progressFill.style.width = (progress * 100).toFixed(1) + "%";
    }

    stage.classList.toggle("has-scrolled", progress > 0.015);
  }

  function smoothLoop() {
    var diff = targetProgress - smoothedProgress;
    if (Math.abs(diff) > 0.0002) {
      // Responsive, fluid easing (0.16) so layers react promptly to scroll without lagging
      smoothedProgress += diff * 0.16;
      renderAtProgress(smoothedProgress);
      requestAnimationFrame(smoothLoop);
    } else {
      smoothedProgress = targetProgress;
      renderAtProgress(smoothedProgress);
      isLoopRunning = false;
    }
  }

  function onScroll() {
    if (!isReady) { return; }
    targetProgress = computeProgress();
    if (!isLoopRunning) {
      isLoopRunning = true;
      requestAnimationFrame(smoothLoop);
    }
  }

  // Only listen when track is near viewport to save CPU
  var trackNearViewport = true;
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      trackNearViewport = entries[0].isIntersecting;
      if (trackNearViewport) { onScroll(); }
    }, { rootMargin: "50% 0px 50% 0px" });
    io.observe(track);
  }

  function scrollGate() {
    if (trackNearViewport) { onScroll(); }
  }

  // Interactive Touch & Drag Scrubbing on the Shoe Stage
  var isDragging = false;
  var dragStartX = 0;
  var dragStartProgress = 0;

  stage.style.cursor = "grab";

  stage.addEventListener("pointerdown", function (e) {
    isDragging = true;
    dragStartX = e.clientX;
    dragStartProgress = smoothedProgress;
    stage.style.cursor = "grabbing";
    stage.setPointerCapture(e.pointerId);
  });

  stage.addEventListener("pointermove", function (e) {
    if (!isDragging) { return; }
    var deltaX = e.clientX - dragStartX;
    // Responsive drag scrubbing across 480px travel
    var newProgress = dragStartProgress + (deltaX / 480);
    if (newProgress < 0) { newProgress = 0; }
    if (newProgress > 1) { newProgress = 1; }
    targetProgress = newProgress;
    if (!isLoopRunning) {
      isLoopRunning = true;
      requestAnimationFrame(smoothLoop);
    }
  });

  // Direct wheel scrubbing on the shoe stage for smooth manual inspection
  stage.addEventListener("wheel", function (e) {
    var delta = e.deltaY;
    if (Math.abs(delta) < 2) { return; }
    var step = (delta > 0 ? 1 : -1) * Math.min(0.08, Math.abs(delta) * 0.0008);
    var nextTarget = targetProgress + step;
    if ((nextTarget >= 0 && nextTarget <= 1) || (targetProgress < 0.95 && delta > 0) || (targetProgress > 0.05 && delta < 0)) {
      e.preventDefault();
      targetProgress = Math.min(1, Math.max(0, nextTarget));
      if (!isLoopRunning) {
        isLoopRunning = true;
        requestAnimationFrame(smoothLoop);
      }
    }
  }, { passive: false });

  function endDrag(e) {
    if (isDragging) {
      isDragging = false;
      stage.style.cursor = "grab";
      try { stage.releasePointerCapture(e.pointerId); } catch (err) {}
    }
  }
  stage.addEventListener("pointerup", endDrag);
  stage.addEventListener("pointercancel", endDrag);

  function activate() {
    isReady = true;
    sizeCanvas();
    targetProgress = computeProgress();
    smoothedProgress = targetProgress;
    stage.classList.add("is-animated");
    renderAtProgress(smoothedProgress);

    window.addEventListener("scroll", scrollGate, { passive: true });
    window.addEventListener("resize", function () {
      sizeCanvas();
      renderAtProgress(smoothedProgress);
    });
  }

  preloadAllFrames(activate);
})();
