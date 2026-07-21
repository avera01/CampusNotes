/**
 * Show/hide toggle for password fields (the eye icon rendered by the
 * password_field() macro in templates/macros.html). Loaded once in
 * base.html so it works on every page that has a password field
 * (login, signup, settings) without each one needing its own script tag.
 */
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".password-toggle").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const wrapper = btn.closest(".password-field");
      const input = wrapper.querySelector("input");
      const willShow = input.type === "password";
      input.type = willShow ? "text" : "password";
      btn.classList.toggle("is-visible", willShow);
      btn.setAttribute("aria-label", willShow ? "Hide password" : "Show password");
    });
  });
});
