/**
 * Instant Light/Dark theme toggle for the Settings page. No save button, no
 * page reload: clicking a button immediately re-themes the current page and
 * writes a cookie so every subsequent page (rendered server-side via the
 * `theme_cookie` context processor) picks up the same choice.
 */
document.addEventListener("DOMContentLoaded", function () {
  const container = document.getElementById("theme-toggle");
  if (!container) return;

  function applyTheme(value) {
    if (value === "light" || value === "dark") {
      document.documentElement.setAttribute("data-theme", value);
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
  }

  function setActiveButton(value) {
    // No explicit cookie yet (first visit) -- highlight whichever theme is
    // actually showing right now, based on the OS preference.
    if (value !== "light" && value !== "dark") {
      value = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }
    container.querySelectorAll(".theme-toggle-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.value === value);
    });
  }

  setActiveButton(container.dataset.current);

  container.querySelectorAll(".theme-toggle-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const value = btn.dataset.value;
      document.cookie = `theme=${value};path=/;max-age=31536000;samesite=Lax`;
      applyTheme(value);
      setActiveButton(value);
    });
  });
});
