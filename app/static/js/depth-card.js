/**
 * React Bits Pro - Depth Card Component (Vanilla JS / High-Performance Edition)
 *
 * Recreates the exact 3D perspective depth effect that responds to mouse movement
 * with multi-layer parallax, dynamic cursor spotlight/glare, and smooth spring physics.
 *
 * Matches https://pro.reactbits.dev/docs/components/depth-card
 */
(function () {
  "use strict";

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var isTouchOnly = window.matchMedia("(pointer: coarse) and (hover: none)").matches;

  function initDepthCards() {
    var cards = document.querySelectorAll("[data-depth-card], .depth-card, [data-product-card]");
    if (!cards.length) { return; }

    cards.forEach(function (card) {
      if (card.__depthCardInitialized) { return; }
      card.__depthCardInitialized = true;

      var inner = card.querySelector(".depth-card-inner") || card;
      var glare = card.querySelector(".depth-card-glare");

      // Auto-inject glare element if missing
      if (!glare) {
        glare = document.createElement("div");
        glare.className = "depth-card-glare";
        glare.setAttribute("aria-hidden", "true");
        inner.appendChild(glare);
      }

      var isProductCard = card.classList.contains("product-card") || card.hasAttribute("data-product-card");
      var defaultRotation = isProductCard ? 8 : 12; // degrees
      var defaultTranslation = isProductCard ? 4 : 6; // px

      var maxRotation = parseFloat(card.getAttribute("data-max-rotation")) || defaultRotation;
      var maxTranslation = parseFloat(card.getAttribute("data-max-translation")) || defaultTranslation;
      var isHovered = false;

      var currentRotX = 0;
      var currentRotY = 0;
      var currentTransX = 0;
      var currentTransY = 0;

      var targetRotX = 0;
      var targetRotY = 0;
      var targetTransX = 0;
      var targetTransY = 0;

      var rafId = null;

      function updateTransform() {
        var ease = isHovered ? 0.14 : 0.08;
        currentRotX += (targetRotX - currentRotX) * ease;
        currentRotY += (targetRotY - currentRotY) * ease;
        currentTransX += (targetTransX - currentTransX) * ease;
        currentTransY += (targetTransY - currentTransY) * ease;

        var liftZ = isHovered ? (isProductCard ? 12 : 16) : 0;

        inner.style.transform =
          "perspective(1000px) rotateX(" +
          currentRotX.toFixed(2) +
          "deg) rotateY(" +
          currentRotY.toFixed(2) +
          "deg) translate3d(" +
          currentTransX.toFixed(2) +
          "px, " +
          currentTransY.toFixed(2) +
          "px, " +
          liftZ +
          "px)";

        if (isHovered) {
          var shadowX = (-currentRotY * 1.2).toFixed(1);
          var shadowY = (currentRotX * 1.2 + 12).toFixed(1);
          inner.style.boxShadow =
            shadowX +
            "px " +
            shadowY +
            "px 28px rgba(23, 26, 30, 0.16), 0 4px 10px rgba(23, 26, 30, 0.05), inset 0 1px 0 rgba(255, 255, 255, 0.95)";
        }

        var delta =
          Math.abs(targetRotX - currentRotX) +
          Math.abs(targetRotY - currentRotY) +
          Math.abs(targetTransX - currentTransX) +
          Math.abs(targetTransY - currentTransY);

        if (delta > 0.01 || isHovered) {
          rafId = requestAnimationFrame(updateTransform);
        } else {
          inner.style.transform = "perspective(1000px) rotateX(0deg) rotateY(0deg) translate3d(0, 0, 0)";
          inner.style.boxShadow = "";
          rafId = null;
        }

      }

      function startLoop() {
        if (!rafId) {
          rafId = requestAnimationFrame(updateTransform);
        }
      }

      if (!reduceMotion && !isTouchOnly) {
        card.addEventListener("pointerenter", function () {
          isHovered = true;
          glare.style.opacity = "1";
          startLoop();
        });

        card.addEventListener("pointermove", function (e) {
          var rect = card.getBoundingClientRect();
          if (!rect.width || !rect.height) { return; }

          var x = e.clientX - rect.left;
          var y = e.clientY - rect.top;

          var normX = (x / rect.width - 0.5) * 2; // -1 to 1
          var normY = (y / rect.height - 0.5) * 2; // -1 to 1

          targetRotX = -normY * maxRotation;
          targetRotY = normX * maxRotation;
          targetTransX = normX * maxTranslation;
          targetTransY = normY * maxTranslation;

          // Position dynamic glare spotlight
          var glarePercentX = (x / rect.width) * 100;
          var glarePercentY = (y / rect.height) * 100;
          var glareOpacity = isProductCard ? 0.22 : 0.32;
          glare.style.background =
            "radial-gradient(circle at " +
            glarePercentX.toFixed(1) +
            "% " +
            glarePercentY.toFixed(1) +
            "%, rgba(255, 255, 255, " +
            glareOpacity +
            ") 0%, rgba(255, 255, 255, 0.06) 32%, transparent 68%)";

          startLoop();
        });

        card.addEventListener("pointerleave", function () {
          isHovered = false;
          targetRotX = 0;
          targetRotY = 0;
          targetTransX = 0;
          targetTransY = 0;
          glare.style.opacity = "0";
          startLoop();
        });
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initDepthCards);
  } else {
    initDepthCards();
  }

  // Export globally so new cards loaded asynchronously can be bound
  window.initDepthCards = initDepthCards;
})();

