/**
 * search.js
 * Debounced live search suggestions under the navbar search box.
 * Pressing Enter still submits the surrounding <form> to /search
 * (server-rendered results page) even if JS fails to load, since
 * the input is a real form field with name="q".
 */

(function () {
    const form = document.getElementById("navbar-search-form");
    const input = document.getElementById("navbar-search-input");
    const suggestionsBox = document.getElementById("navbar-search-suggestions");

    if (!form || !input || !suggestionsBox) return;

    let debounceTimer = null;
    let activeIndex = -1;

    function closeSuggestions() {
        suggestionsBox.hidden = true;
        suggestionsBox.innerHTML = "";
        activeIndex = -1;
    }

    function renderSuggestions(movies) {
        if (!movies.length) {
            suggestionsBox.innerHTML = '<div class="navbar-search-empty">No matches yet</div>';
            suggestionsBox.hidden = false;
            return;
        }

        const esc = window.MovieStream.escapeHTML;
        suggestionsBox.innerHTML = movies
            .map(
                (movie, index) => `
                <a href="/movie/${Number(movie.id)}" class="navbar-search-item" data-index="${index}">
                    <div class="navbar-search-item-poster">
                        ${
                            movie.poster_url
                                ? `<img src="${esc(movie.poster_url)}" alt="">`
                                : `<span>${esc(movie.title.charAt(0))}</span>`
                        }
                    </div>
                    <div class="navbar-search-item-info">
                        <p>${esc(movie.title)}</p>
                        <span>${esc(movie.release_year)} &middot; ${esc(movie.genre)}</span>
                    </div>
                </a>`
            )
            .join("");
        suggestionsBox.hidden = false;
    }

    async function runSearch(q) {
        try {
            const data = await window.MovieStreamAPI.searchMovies({ q, limit: 6 });
            renderSuggestions(data.movies);
        } catch (err) {
            closeSuggestions();
        }
    }

    input.addEventListener("input", () => {
        const q = input.value.trim();
        clearTimeout(debounceTimer);
        if (!q) {
            closeSuggestions();
            return;
        }
        debounceTimer = setTimeout(() => runSearch(q), 250);
    });

    input.addEventListener("keydown", (event) => {
        const items = suggestionsBox.querySelectorAll(".navbar-search-item");
        if (!items.length || suggestionsBox.hidden) return;

        if (event.key === "ArrowDown") {
            event.preventDefault();
            activeIndex = Math.min(activeIndex + 1, items.length - 1);
        } else if (event.key === "ArrowUp") {
            event.preventDefault();
            activeIndex = Math.max(activeIndex - 1, 0);
        } else if (event.key === "Enter" && activeIndex >= 0) {
            event.preventDefault();
            window.location.href = items[activeIndex].getAttribute("href");
            return;
        } else {
            return;
        }

        items.forEach((item, i) => item.classList.toggle("active", i === activeIndex));
        items[activeIndex].scrollIntoView({ block: "nearest" });
    });

    document.addEventListener("click", (event) => {
        if (!form.contains(event.target)) closeSuggestions();
    });
})();
