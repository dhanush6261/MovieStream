/**
 * auth.js
 * Scoped to /profile/edit: shows a live preview of the selected
 * avatar image before the form is submitted.
 */

(function () {
    const input = document.getElementById("avatar-input");
    const previewImg = document.getElementById("avatar-preview-img");
    if (!input || !previewImg) return;

    input.addEventListener("change", () => {
        const file = input.files && input.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (event) => {
            previewImg.src = event.target.result;
        };
        reader.readAsDataURL(file);
    });
})();
