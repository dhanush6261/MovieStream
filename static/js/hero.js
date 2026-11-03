/**
 * hero.js
 * Wires the three hero banner buttons. Only runs if a hero section
 * with data-movie-id is present (the "no movies yet" empty hero has
 * no buttons to wire).
 */

(function () {
    const heroContent = document.querySelector(".hero-content[data-movie-id]");
    if (!heroContent) return;

    const movieId = heroContent.dataset.movieId;
    const title = heroContent.dataset.movieTitle;

    const playBtn = heroContent.querySelector('[data-hero-action="play"]');
    const trailerBtn = heroContent.querySelector('[data-hero-action="trailer"]');
    const myListBtn = heroContent.querySelector('[data-hero-action="mylist"]');

    if (playBtn) {
        playBtn.addEventListener("click", () => {
            window.location.href = `/movie/${movieId}?autoplay=1`;
        });
    }

    if (trailerBtn) {
        trailerBtn.addEventListener("click", () => {
            window.MovieStream.openTrailerModal(trailerBtn.dataset.trailerUrl, title);
        });
    }

    if (myListBtn) {
        const syncState = () => {
            const active = window.MovieStream.isInMyList(movieId);
            myListBtn.classList.toggle("is-active", active);
            myListBtn.setAttribute("aria-pressed", String(active));
        };
        syncState();
        myListBtn.addEventListener("click", () => {
            window.MovieStream.toggleMyList(movieId, title);
            syncState();
        });
    }
})();
