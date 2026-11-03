/**
 * movie-card.js
 * Event delegation on document.body so this works for movie cards
 * rendered server-side (home/search pages) AND cards built
 * dynamically in JS (the My List page). One listener, not one per
 * card, per button.
 */

(function () {
    const WATCH_LATER_KEY = "moviestream_watch_later";

    function getWatchLater() {
        try {
            return JSON.parse(localStorage.getItem(WATCH_LATER_KEY)) || [];
        } catch (err) {
            return [];
        }
    }

    function toggleWatchLater(movieId, title, button) {
        const id = Number(movieId);
        let list = getWatchLater();
        let added;
        if (list.includes(id)) {
            list = list.filter((existing) => existing !== id);
            added = false;
        } else {
            list.push(id);
            added = true;
        }
        localStorage.setItem(WATCH_LATER_KEY, JSON.stringify(list));
        button.classList.toggle("is-active", added);
        button.setAttribute("aria-pressed", String(added));
        window.MovieStream.toast(
            added ? `Added "${title}" to Watch Later` : `Removed "${title}" from Watch Later`,
            "success"
        );
    }

    function refreshWatchLaterButtons() {
        const list = getWatchLater();
        document.querySelectorAll('[data-action="watch-later"]').forEach((btn) => {
            const active = list.includes(Number(btn.dataset.movieId));
            btn.classList.toggle("is-active", active);
            btn.setAttribute("aria-pressed", String(active));
        });
    }

    document.addEventListener("click", (event) => {
        const button = event.target.closest("[data-action]");
        if (!button) return;

        const action = button.dataset.action;
        const movieId = button.dataset.movieId;
        const card = button.closest("[data-movie-title]");
        const title = (card && card.dataset.movieTitle) || "";

        if (action === "play") {
            event.preventDefault();
            window.location.href = `/movie/${movieId}?autoplay=1`;
        } else if (action === "mylist") {
            event.preventDefault();
            window.MovieStream.toggleMyList(movieId, title);
        } else if (action === "watch-later") {
            event.preventDefault();
            toggleWatchLater(movieId, title, button);
        } else if (action === "share") {
            event.preventDefault();
            const url = `${window.location.origin}/movie/${movieId}`;
            window.MovieStream.shareMovie(title, url);
        } else if (action === "trailer") {
            event.preventDefault();
            const trailerUrl = button.dataset.trailerUrl;
            window.MovieStream.openTrailerModal(trailerUrl, title);
        }
    });

    document.addEventListener("DOMContentLoaded", refreshWatchLaterButtons);
    window.addEventListener("moviestream:cards-rendered", refreshWatchLaterButtons);
})();
