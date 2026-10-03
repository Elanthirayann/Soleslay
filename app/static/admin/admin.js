// Confirmation dialogs for any destructive action.
document.addEventListener("submit", function (e) {
  const form = e.target;
  if (form.matches("[data-confirm]")) {
    const message = form.getAttribute("data-confirm") || "Are you sure?";
    if (!window.confirm(message)) {
      e.preventDefault();
    }
  }
});

// Drag-and-drop image upload zones. Any element with [data-dropzone]
// wraps a hidden <input type="file" multiple> with the given id; dropping
// files (or picking them normally) previews filenames and submits on click.
document.querySelectorAll("[data-dropzone]").forEach(function (zone) {
  const inputId = zone.getAttribute("data-dropzone");
  const input = document.getElementById(inputId);
  if (!input) return;
  const label = zone.querySelector("[data-dropzone-label]");
  const defaultText = label ? label.textContent : "";

  function updatePreview() {
    if (!label) return;
    if (input.files && input.files.length) {
      const names = Array.from(input.files).map(f => f.name).join(", ");
      label.textContent = `${input.files.length} file(s) selected: ${names}`;
    } else {
      label.textContent = defaultText;
    }
  }

  zone.addEventListener("click", () => input.click());
  input.addEventListener("change", updatePreview);

  ["dragenter", "dragover"].forEach(evt =>
    zone.addEventListener(evt, e => {
      e.preventDefault();
      zone.classList.add("dragover");
    })
  );
  ["dragleave", "drop"].forEach(evt =>
    zone.addEventListener(evt, e => {
      e.preventDefault();
      zone.classList.remove("dragover");
    })
  );
  zone.addEventListener("drop", e => {
    if (e.dataTransfer.files && e.dataTransfer.files.length) {
      input.files = e.dataTransfer.files;
      updatePreview();
    }
  });
});

// Auto-slugify: any [data-slug-source] input fills a [data-slug-target]
// input as the user types, unless the target has already been hand-edited.
document.querySelectorAll("[data-slug-source]").forEach(function (source) {
  const targetId = source.getAttribute("data-slug-source");
  const target = document.getElementById(targetId);
  if (!target) return;
  let edited = target.value.trim().length > 0;
  target.addEventListener("input", () => { edited = true; });
  source.addEventListener("input", () => {
    if (edited) return;
    target.value = source.value
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
  });
});

// Mobile sidebar drawer: hamburger opens it, the close button, backdrop
// click, Escape key, or tapping a nav link all close it again.
(function () {
  const toggle = document.getElementById("admin-menu-toggle");
  const sidebar = document.getElementById("admin-sidebar");
  const backdrop = document.getElementById("admin-sidebar-backdrop");
  const closeBtn = document.getElementById("admin-sidebar-close");
  if (!toggle || !sidebar || !backdrop) return;

  const isMobile = () => window.matchMedia("(max-width: 900px)").matches;
  // Only mark it hidden-from-assistive-tech while it's actually the
  // closed, off-screen mobile drawer — never on desktop, where it's a
  // permanently visible sidebar.
  if (isMobile()) sidebar.setAttribute("aria-hidden", "true");

  function openSidebar() {
    sidebar.classList.add("is-open");
    sidebar.setAttribute("aria-hidden", "false");
    backdrop.hidden = false;
    requestAnimationFrame(() => backdrop.classList.add("is-open"));
    toggle.setAttribute("aria-expanded", "true");
    document.body.style.overflow = "hidden";
  }

  function closeSidebar() {
    sidebar.classList.remove("is-open");
    sidebar.setAttribute("aria-hidden", "true");
    backdrop.classList.remove("is-open");
    toggle.setAttribute("aria-expanded", "false");
    document.body.style.overflow = "";
    window.setTimeout(() => { backdrop.hidden = true; }, 200);
  }

  toggle.addEventListener("click", openSidebar);
  if (closeBtn) closeBtn.addEventListener("click", closeSidebar);
  backdrop.addEventListener("click", closeSidebar);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && sidebar.classList.contains("is-open")) closeSidebar();
  });
  sidebar.querySelectorAll(".admin-nav a").forEach((link) => {
    link.addEventListener("click", closeSidebar);
  });

  // If the viewport is resized past the mobile breakpoint while the
  // drawer is open, reset everything so it doesn't get stuck mid-state.
  window.addEventListener("resize", () => {
    if (window.innerWidth > 900 && sidebar.classList.contains("is-open")) {
      closeSidebar();
    }
  });
})();
