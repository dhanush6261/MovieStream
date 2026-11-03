/**
 * upload.js
 * Two things, both scoped to the /upload page:
 *   1. Submits the form via XHR instead of a plain browser POST so we
 *      can show a real, byte-accurate progress bar while the video
 *      uploads, then hands off to whatever page the server ends up
 *      rendering (success redirect to the movie page, or the same
 *      upload form re-rendered with validation errors).
 *   2. Wires the "Scan Library Folder" button to POST /api/movies/scan.
 */

(function () {
    const form = document.getElementById("upload-form");
    if (!form) return;

    const submitBtn = document.getElementById("upload-submit-btn");
    const progressWrap = document.getElementById("upload-progress-wrap");
    const progressBar = document.getElementById("upload-progress-bar");
    const progressLabel = document.getElementById("upload-progress-label");
    const maxUploadBytes = Number(form.dataset.maxUploadBytes) || Infinity;

    function formatGb(bytes) {
        return (bytes / 1024 / 1024 / 1024).toFixed(1);
    }

    form.addEventListener("submit", (event) => {
        event.preventDefault();

        // Pre-flight size check: fail fast in the browser instead of
        // uploading gigabytes only to be rejected by the server.
        const videoInput = form.querySelector('input[type="file"][name="video"]');
        const videoFile = videoInput && videoInput.files[0];
        if (videoFile && videoFile.size > maxUploadBytes) {
            window.MovieStream.toast(
                `That file is ${formatGb(videoFile.size)} GB, which is over the ${formatGb(maxUploadBytes)} GB upload limit.`,
                "error"
            );
            return;
        }

        const formData = new FormData(form);
        const xhr = new XMLHttpRequest();
        xhr.open("POST", form.action || window.location.href, true);

        submitBtn.disabled = true;
        submitBtn.textContent = "Uploading...";
        progressWrap.hidden = false;
        progressLabel.textContent = "Uploading... 0%";

        xhr.upload.addEventListener("progress", (progressEvent) => {
            if (!progressEvent.lengthComputable) return;
            const percent = Math.round((progressEvent.loaded / progressEvent.total) * 100);
            progressBar.style.width = `${percent}%`;
            progressLabel.textContent = `Uploading... ${percent}%`;
        });

        xhr.addEventListener("load", () => {
            if (xhr.status >= 400) {
                submitBtn.disabled = false;
                submitBtn.textContent = "Upload Movie";
                if (xhr.status === 413) {
                    window.MovieStream.toast(
                        `That file is too large for the current upload limit (${formatGb(maxUploadBytes)} GB).`,
                        "error"
                    );
                    progressLabel.textContent = "Upload failed - file too large.";
                    return;
                }
                // Any other server-rendered error (e.g. validation, duplicate
                // video) re-renders the form with its own flash/field errors.
            }
            document.open();
            document.write(xhr.responseText);
            document.close();
            if (xhr.responseURL) {
                history.replaceState(null, "", xhr.responseURL);
            }
        });

        xhr.addEventListener("error", () => {
            submitBtn.disabled = false;
            submitBtn.textContent = "Upload Movie";
            progressLabel.textContent = "Upload failed - check your connection and try again.";
        });

        xhr.send(formData);
    });

    const scanBtn = document.getElementById("scan-library-btn");
    if (scanBtn) {
        scanBtn.addEventListener("click", async () => {
            scanBtn.disabled = true;
            scanBtn.textContent = "Scanning...";
            try {
                const result = await window.MovieStreamAPI.scanLibrary();
                if (result.created_count > 0) {
                    window.MovieStream.toast(
                        `Found and added ${result.created_count} new movie(s) from the library folder.`,
                        "success"
                    );
                } else {
                    window.MovieStream.toast("No new files found in the movies folder.", "info");
                }
            } catch (err) {
                window.MovieStream.toast(err.message || "Scan failed.", "error");
            } finally {
                scanBtn.disabled = false;
                scanBtn.textContent = "Scan Library Folder";
            }
        });
    }
})();
