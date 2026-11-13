/**
 * my-list.js
 * Scoped to /my-list. Reads the locally-stored watchlist ids,
 * fetches their full data from the API, and renders cards using the
 * same markup/classes as the server-rendered macro so styling stays
 * consistent. Removing an item from My List while on this page
 * removes its card immediately.
 */

(function () {
    const grid = document.getElementById("my-list-grid");
    if (!grid) return;

    function cardHTML(movie) {
        const esc = window.MovieStream.escapeHTML;
        const id = Number(movie.id);
        const title = esc(movie.title);
        const posterInner = movie.poster_url
            ? `<img src="${esc(movie.poster_url)}" alt="${title} poster" loading="lazy">`
            : `<div class="movie-card-placeholder"><span>${esc(movie.title.charAt(0))}</span></div>`;

        return `
        <div class="movie-card" tabindex="0" data-movie-id="${id}" data-movie-title="${title}">
            <div class="movie-card-poster">
                ${posterInner}
                <div class="movie-card-overlay">
                    <div class="movie-card-buttons">
                        <button class="movie-card-btn movie-card-btn-play" data-action="play" data-movie-id="${id}" title="Play" aria-label="Play ${title}">
                            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
                        </button>
                        <button class="movie-card-btn is-active" data-action="mylist" data-movie-id="${id}" title="Remove from My List" aria-label="Remove ${title} from my list" aria-pressed="true">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
                        </button>
                        <button class="movie-card-btn" data-action="share" data-movie-id="${id}" title="Share" aria-label="Share ${title}">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.6 13.5l6.8 3.9M15.4 6.6L8.6 10.5"/></svg>
                        </button>
                    </div>
                </div>
            </div>
            <a class="movie-card-info" href="/movie/${id}">
                <p class="movie-card-title">${title}</p>
                <div class="movie-card-meta">
                    <span class="movie-card-rating">&#9733; ${Number(movie.rating).toFixed(1)}</span>
                    <span>${esc(movie.release_year)}</span>
                    <span>${esc(movie.runtime_display)}</span>
                    <span>${esc(movie.language)}</span>
                </div>
            </a>
        </div>`;
    }

    function showEmpty() {
        grid.innerHTML = `
            <div class="empty-state">
                <p>Your list is empty. Add movies with the "My List" button on any title.</p>
                <a href="/" class="btn btn-primary">Browse Movies</a>
            </div>`;
    }

    async function load() {
        const ids = window.MovieStream.getMyList();
        if (!ids.length) {
            showEmpty();
            return;
        }
        try {
            const data = await window.MovieStreamAPI.getMoviesByIds(ids);
            if (!data.movies.length) {
                showEmpty();
                return;
            }
            grid.innerHTML = data.movies.map(cardHTML).join("");
            window.dispatchEvent(new Event("moviestream:cards-rendered"));
            window.MovieStream.refreshMyListButtons();
        } catch (err) {
            grid.innerHTML = `<p class="empty-state">Couldn't load your list right now.</p>`;
        }
    }

    grid.addEventListener("click", (event) => {
        const btn = event.target.closest('[data-action="mylist"]');
        if (!btn) return;
        requestAnimationFrame(() => {
            if (!window.MovieStream.isInMyList(btn.dataset.movieId)) {
                const card = btn.closest(".movie-card");
                if (card) card.remove();
                if (!grid.querySelector(".movie-card")) showEmpty();
            }
        });
    });

    load();
})();
