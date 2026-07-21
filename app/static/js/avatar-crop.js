/**
 * Profile picture upload with client-side cropping (Cropper.js, loaded via
 * CDN in settings.html -- see that file's <head> block).
 *
 * Flow: choose a file -> validate type/size in the browser -> open the crop
 * modal -> user drags/zooms (Cropper.js also updates the circular live
 * preview automatically via its `preview` option) -> "Save picture" reads
 * a 300x300 canvas out of the cropper, converts it to a JPEG Blob, and
 * uploads it with fetch(). Nothing is ever a raw, unprocessed file upload --
 * the server (see app/auth/avatar_storage.py) re-validates and re-processes
 * it anyway, but the crop the user sees is exactly what gets sent.
 *
 * On success the settings-page preview and the nav avatar are updated
 * directly from the JSON response -- no page reload. On any failure
 * (bad file, network error, server rejection) an inline message is shown
 * and the crop modal stays open so the user can retry.
 */
document.addEventListener("DOMContentLoaded", function () {
  const fileInput = document.getElementById("avatar-file-input");
  const chooseBtn = document.getElementById("avatar-choose-btn");
  if (!fileInput || !chooseBtn) return; // Settings page isn't loaded

  const errorEl = document.getElementById("avatar-error");

  const overlay = document.getElementById("avatar-crop-overlay");
  const uploadUrl = overlay.dataset.uploadUrl;
  const cropperImage = document.getElementById("cropper-image");
  const cropError = document.getElementById("crop-error");
  const zoomInBtn = document.getElementById("cropper-zoom-in");
  const zoomOutBtn = document.getElementById("cropper-zoom-out");
  const saveBtn = document.getElementById("cropper-save");
  const cancelBtn = document.getElementById("cropper-cancel");

  const previewImg = document.getElementById("avatar-preview-img");
  const previewFallback = document.getElementById("avatar-preview-fallback");
  const removeForm = document.getElementById("remove-avatar-form");

  const navImg = document.getElementById("nav-avatar-img");
  const navFallback = document.getElementById("nav-avatar-fallback");

  const csrfInput = document.getElementById("avatar-csrf-token");

  const MAX_BYTES = 5 * 1024 * 1024; // 5MB, mirrors AvatarForm's FileSize validator
  const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];
  const OUTPUT_SIZE = 300; // must match AVATAR_SIZE in avatar_storage.py

  let cropper = null;
  let objectUrl = null;

  function showError(el, message) {
    el.textContent = message;
    el.hidden = false;
  }

  function hideError(el) {
    el.hidden = true;
    el.textContent = "";
  }

  function resetSaveButton() {
    saveBtn.disabled = false;
    saveBtn.textContent = "Save picture";
  }

  function openCropper(file) {
    hideError(cropError);
    overlay.hidden = false;

    // IMPORTANT: attach onload/onerror BEFORE setting .src. Local blob:
    // URLs can finish decoding fast enough that `load` fires before the
    // next line even runs -- if the handler isn't attached yet, it's
    // silently missed, Cropper never initializes, and every control below
    // (zoom, Save) becomes a no-op since they all check `if (cropper)`.
    // That's what "the page is frozen" actually was: not a crash, just a
    // cropper that was never created.
    cropperImage.onload = function () {
      // Cropper.js needs the image's natural dimensions, which aren't
      // available until the browser has actually loaded/decoded it.
      if (cropper) cropper.destroy();
      try {
        cropper = new Cropper(cropperImage, {
          aspectRatio: 1, // lock to a square, since avatars display as circles
          viewMode: 1, // don't let the crop box leave the image
          dragMode: "move",
          autoCropArea: 1,
          cropBoxMovable: false,
          cropBoxResizable: false,
          toggleDragModeOnDblclick: false,
          preview: "#avatar-live-preview", // Cropper keeps this in sync automatically
        });
      } catch (err) {
        // Most likely cause: the Cropper.js CDN script failed to load.
        showError(cropError, "Couldn't open the photo editor. Please try again.");
      }
    };

    // A file can pass the browser's MIME-type check (file.type) yet still
    // be corrupt or not actually decodable as an image -- without this,
    // onload above would simply never fire and the user would be stuck
    // looking at a modal with a broken image and no way forward.
    cropperImage.onerror = function () {
      showError(cropError, "That file couldn't be opened as an image. Try a different photo.");
    };

    // Now that both handlers are attached, it's safe to trigger the load.
    objectUrl = URL.createObjectURL(file);
    cropperImage.src = objectUrl;
  }

  function closeCropper() {
    overlay.hidden = true;
    if (cropper) {
      cropper.destroy();
      cropper = null;
    }
    if (objectUrl) {
      URL.revokeObjectURL(objectUrl);
      objectUrl = null;
    }
    fileInput.value = "";
  }

  function updateAvatarDisplay(avatarUrl) {
    if (previewImg && previewFallback) {
      previewImg.src = avatarUrl;
      previewImg.hidden = false;
      previewFallback.hidden = true;
    }
    if (navImg && navFallback) {
      navImg.src = avatarUrl;
      navImg.hidden = false;
      navFallback.hidden = true;
    }
    if (removeForm) removeForm.hidden = false;
  }

  chooseBtn.addEventListener("click", function () {
    fileInput.click();
  });

  fileInput.addEventListener("change", function () {
    hideError(errorEl);
    const file = fileInput.files[0];
    if (!file) return;

    if (!ALLOWED_TYPES.includes(file.type)) {
      showError(errorEl, "Please choose a JPG, PNG, or WEBP image.");
      fileInput.value = "";
      return;
    }
    if (file.size > MAX_BYTES) {
      showError(errorEl, "Image must be 5MB or smaller.");
      fileInput.value = "";
      return;
    }

    openCropper(file);
  });

  zoomInBtn.addEventListener("click", function () {
    if (cropper) cropper.zoom(0.1);
  });
  zoomOutBtn.addEventListener("click", function () {
    if (cropper) cropper.zoom(-0.1);
  });

  cancelBtn.addEventListener("click", closeCropper);

  saveBtn.addEventListener("click", function () {
    if (!cropper) return;
    hideError(cropError);
    saveBtn.disabled = true;
    saveBtn.textContent = "Saving...";

    const canvas = cropper.getCroppedCanvas({
      width: OUTPUT_SIZE,
      height: OUTPUT_SIZE,
      imageSmoothingQuality: "high",
    });

    if (!canvas) {
      showError(cropError, "Couldn't process that image. Try a different photo.");
      resetSaveButton();
      return;
    }

    canvas.toBlob(function (blob) {
      if (!blob) {
        showError(cropError, "Couldn't process that image. Try a different photo.");
        resetSaveButton();
        return;
      }

      const formData = new FormData();
      formData.append("avatar", blob, "avatar.jpg");
      formData.append("csrf_token", csrfInput.value);

      fetch(uploadUrl, { method: "POST", body: formData })
        .then(function (response) {
          return response.json().then(function (data) {
            return { ok: response.ok, data: data };
          });
        })
        .then(function (result) {
          if (!result.ok || !result.data.success) {
            throw new Error(result.data.error || "Upload failed. Please try again.");
          }
          updateAvatarDisplay(result.data.avatar_url);
          closeCropper();
        })
        .catch(function (err) {
          showError(cropError, err.message || "Upload failed. Please try again.");
        })
        .finally(resetSaveButton);
    }, "image/jpeg", 0.9);
  });
});
