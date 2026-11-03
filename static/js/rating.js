/**
 * rating.js
 * Movie rating UI and API integration.
 */

(function () {
    const ratingContainer = document.getElementById("movie-rating");

    if (!ratingContainer) return;

    const movieId = ratingContainer.dataset.movieId;

    const stars = Array.from(
        ratingContainer.querySelectorAll(".rating-star")
    );

    const averageEl = document.getElementById("movie-rating-average");
    const statusEl = document.getElementById("movie-rating-status");
    const removeBtn = document.getElementById("movie-rating-remove");

    let currentRating = null;
    let isSubmitting = false;

    // ---------------------------------------------------------
    // Status message
    // ---------------------------------------------------------

    function setStatus(message, type = "info") {
        if (!statusEl) return;

        statusEl.textContent = message;
        statusEl.dataset.type = type;
    }

    // ---------------------------------------------------------
    // Highlight selected stars
    // ---------------------------------------------------------

    function highlightStars(rating) {
        stars.forEach((star) => {
            const value = Number(star.dataset.rating);

            star.classList.toggle(
                "is-selected",
                rating !== null && value <= rating
            );
        });
    }

    // ---------------------------------------------------------
    // Hover preview
    // ---------------------------------------------------------

    function previewStars(rating) {
        stars.forEach((star) => {
            const value = Number(star.dataset.rating);

            star.classList.toggle(
                "is-hovered",
                value <= rating
            );
        });
    }

    function clearPreview() {
        stars.forEach((star) => {
            star.classList.remove("is-hovered");
        });

        highlightStars(currentRating);
    }

    // ---------------------------------------------------------
    // Update average rating
    // ---------------------------------------------------------

    function updateAverage(data) {
        if (!averageEl) return;

        const average = Number(data.average_rating || 0);

        averageEl.textContent = `★ ${average.toFixed(1)}`;
    }

    // ---------------------------------------------------------
    // Update user's rating
    // ---------------------------------------------------------

    function updateCurrentRating(rating) {
        currentRating =
            rating === null || rating === undefined
                ? null
                : Number(rating);

        highlightStars(currentRating);

        if (removeBtn) {
            removeBtn.hidden = currentRating === null;
        }
    }

    // ---------------------------------------------------------
    // Disable / enable stars
    // ---------------------------------------------------------

    function setStarsDisabled(disabled) {
        stars.forEach((star) => {
            star.disabled = disabled;
        });
    }

    // ---------------------------------------------------------
    // Load existing rating
    // ---------------------------------------------------------

    async function loadRating() {
        try {
            const data =
                await window.MovieStreamAPI.getMovieRating(movieId);

            updateAverage(data);
            updateCurrentRating(data.user_rating);

            if (data.user_rating !== null) {
                setStatus(
                    `Your rating: ${data.user_rating}/10`,
                    "success"
                );
            }
        } catch (error) {
            console.error("Failed to load movie rating:", error);

            setStatus(
                "Couldn't load rating.",
                "error"
            );
        }
    }

    // ---------------------------------------------------------
    // Submit rating
    // ---------------------------------------------------------

    async function submitRating(rating) {
        if (isSubmitting) return;

        isSubmitting = true;
        setStarsDisabled(true);

        try {
            const data =
                await window.MovieStreamAPI.submitMovieRating(
                    movieId,
                    rating
                );

            updateAverage(data);
            updateCurrentRating(data.user_rating);

            setStatus(
                `You rated this movie ${rating}/10.`,
                "success"
            );
        } catch (error) {
            console.error("Failed to save movie rating:", error);

            if (error.status === 401) {
                setStatus(
                    "Please log in to rate this movie.",
                    "error"
                );
            } else {
                setStatus(
                    error.message ||
                    "Couldn't save your rating.",
                    "error"
                );
            }
        } finally {
            isSubmitting = false;
            setStarsDisabled(false);
        }
    }

    // ---------------------------------------------------------
    // Remove rating
    // ---------------------------------------------------------

    async function removeRating() {
        if (isSubmitting) return;

        isSubmitting = true;

        if (removeBtn) {
            removeBtn.disabled = true;
        }

        try {
            const data =
                await window.MovieStreamAPI.deleteMovieRating(
                    movieId
                );

            updateAverage(data);
            updateCurrentRating(null);

            setStatus(
                "Your rating has been removed.",
                "success"
            );
        } catch (error) {
            console.error("Failed to remove movie rating:", error);

            if (error.status === 401) {
                setStatus(
                    "Please log in to remove your rating.",
                    "error"
                );
            } else {
                setStatus(
                    error.message ||
                    "Couldn't remove your rating.",
                    "error"
                );
            }
        } finally {
            isSubmitting = false;

            if (removeBtn) {
                removeBtn.disabled = false;
            }
        }
    }

    // ---------------------------------------------------------
    // Star events
    // ---------------------------------------------------------

    stars.forEach((star) => {

        star.addEventListener("mouseenter", () => {
            const rating =
                Number(star.dataset.rating);

            previewStars(rating);
        });

        star.addEventListener("mouseleave", () => {
            clearPreview();
        });

        star.addEventListener("focus", () => {
            const rating =
                Number(star.dataset.rating);

            previewStars(rating);
        });

        star.addEventListener("blur", () => {
            clearPreview();
        });

        star.addEventListener("click", () => {
            const rating =
                Number(star.dataset.rating);

            submitRating(rating);
        });
    });

    // ---------------------------------------------------------
    // Remove button
    // ---------------------------------------------------------

    if (removeBtn) {
        removeBtn.addEventListener(
            "click",
            removeRating
        );
    }

    // ---------------------------------------------------------
    // Initial load
    // ---------------------------------------------------------

    loadRating();

})();