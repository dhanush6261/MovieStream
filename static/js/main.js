/**
 * main.js
 * Shared utilities used by hero.js, movie-card.js, and search.js:
 *   - toast(): small notification popups
 *   - MyList: server-side Favorites (via /api/favorites) when logged
 *     in, falling back to a localStorage watchlist for guests so the
 *     feature still works without an account
 *   - Trailer modal open/close
 *
 * Loaded once, site-wide, before the feature-specific scripts.
 */

window.MovieStream = (function () {
    const MY_LIST_KEY = "moviestream_my_list";

    // --- Toasts -------------------------------------------------------
    function toast(message, type = "info") {
        let container = document.getElementById("toast-container");
        if (!container) {
            container = document.createElement("div");
            container.id = "toast-container";
            container.className = "toast-container";
            document.body.appendChild(container);
        }
        const el = document.createElement("div");
        el.className = `toast toast-${type}`;
        el.textContent = message;
        container.appendChild(el);

        requestAnimationFrame(() => el.classList.add("toast-visible"));
        setTimeout(() => {
            el.classList.remove("toast-visible");
            setTimeout(() => el.remove(), 300);
        }, 3000);
    }

    // Escape API data before it goes into innerHTML. Movie titles etc.
    // are user-editable, so interpolating them raw is stored XSS.
    function escapeHTML(value) {
        return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function isAuthenticated() {
        return document.body.dataset.authenticated === "true";
    }

    // --- My List: localStorage (guests) ---------------------------------
    function getLocalList() {
        try {
            return JSON.parse(localStorage.getItem(MY_LIST_KEY)) || [];
        } catch (err) {
            return [];
        }
    }

    function setLocalList(list) {
        localStorage.setItem(MY_LIST_KEY, JSON.stringify(list));
    }

    // --- My List: server-side Favorites (logged-in users) -----------------
    // Cached in memory after the first load so isInMyList() can stay
    // synchronous (buttons need to render their active state
    // immediately, not after an awaited fetch resolves).
    let serverFavoriteIds = null;

    async function loadServerFavorites() {
        if (!isAuthenticated()) return;
        try {
            const data = await window.MovieStreamAPI.getFavorites();
            serverFavoriteIds = new Set(data.movies.map((m) => m.id));
        } catch (err) {
            serverFavoriteIds = new Set();
        }
        refreshMyListButtons();
    }

    // --- Public My List API ------------------------------------------------
    function getMyList() {
        if (isAuthenticated()) {
            return serverFavoriteIds ? Array.from(serverFavoriteIds) : [];
        }
        return getLocalList();
    }

    function isInMyList(movieId) {
        const id = Number(movieId);
        if (isAuthenticated()) {
            return serverFavoriteIds ? serverFavoriteIds.has(id) : false;
        }
        return getLocalList().includes(id);
    }

    function toggleMyList(movieId, title) {
        const id = Number(movieId);

        if (isAuthenticated()) {
            const currentlyIn = serverFavoriteIds && serverFavoriteIds.has(id);
            const action = currentlyIn
                ? window.MovieStreamAPI.removeFavorite(id)
                : window.MovieStreamAPI.addFavorite(id);

            action
                .then(() => {
                    if (!serverFavoriteIds) serverFavoriteIds = new Set();
                    if (currentlyIn) {
                        serverFavoriteIds.delete(id);
                    } else {
                        serverFavoriteIds.add(id);
                    }
                    toast(
                        currentlyIn ? `Removed "${title}" from My List` : `Added "${title}" to My List`,
                        "success"
                    );
                    refreshMyListButtons();
                    window.dispatchEvent(new CustomEvent("moviestream:favorites-changed"));
                })
                .catch(() => toast("Couldn't update My List. Try again.", "error"));

            return !currentlyIn;
        }

        // Guest: localStorage.
        let list = getLocalList();
        let added;
        if (list.includes(id)) {
            list = list.filter((existing) => existing !== id);
            added = false;
        } else {
            list.push(id);
            added = true;
        }
        setLocalList(list);
        toast(added ? `Added "${title}" to My List` : `Removed "${title}" from My List`, "success");
        refreshMyListButtons();
        return added;
    }

    function refreshMyListButtons() {
        const list = getMyList();
        const buttons = document.querySelectorAll(
            '[data-action="mylist"], [data-hero-action="mylist"]'
        );
        buttons.forEach((btn) => {
            const id = Number(btn.dataset.movieId);
            if (!id) return;
            const active = list.includes(id);
            btn.classList.toggle("is-active", active);
            btn.setAttribute("aria-pressed", String(active));
        });
    }

    // --- Migrate a guest's localStorage list onto a freshly logged-in account ---
    async function syncGuestListToServer() {
        if (!isAuthenticated()) return;
        const guestIds = getLocalList();
        if (!guestIds.length) return;
        try {
            await window.MovieStreamAPI.syncFavorites(guestIds);
            localStorage.removeItem(MY_LIST_KEY);
            await loadServerFavorites();
        } catch (err) {
            // Non-fatal: the guest list just stays in localStorage, unused, until this succeeds later.
        }
    }

    // --- Trailer modal ---------------------------------------------------
    function ensureTrailerModal() {
        let modal = document.getElementById("trailer-modal");
        if (modal) return modal;

        modal = document.createElement("div");
        modal.id = "trailer-modal";
        modal.className = "trailer-modal";
        modal.innerHTML = `
            <div class="trailer-modal-backdrop" data-close-trailer></div>
            <div class="trailer-modal-box">
                <button class="trailer-modal-close" data-close-trailer aria-label="Close trailer">&times;</button>
                <video class="trailer-modal-video" controls playsinline></video>
                <p class="trailer-modal-title"></p>
            </div>
        `;
        document.body.appendChild(modal);

        modal.querySelectorAll("[data-close-trailer]").forEach((el) => {
            el.addEventListener("click", closeTrailerModal);
        });
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") closeTrailerModal();
        });

        return modal;
    }

    function openTrailerModal(trailerUrl, title) {
        if (!trailerUrl) {
            toast("No trailer available for this title yet.", "info");
            return;
        }
        const modal = ensureTrailerModal();
        const video = modal.querySelector(".trailer-modal-video");
        const titleEl = modal.querySelector(".trailer-modal-title");
        video.src = trailerUrl;
        titleEl.textContent = title || "";
        modal.classList.add("open");
        video.currentTime = 0;
        video.play().catch(() => {
            /* Autoplay can be blocked by the browser; the visible controls let the user press play. */
        });
    }

    function closeTrailerModal() {
        const modal = document.getElementById("trailer-modal");
        if (!modal) return;
        const video = modal.querySelector(".trailer-modal-video");
        video.pause();
        video.src = "";
        modal.classList.remove("open");
    }

    // --- Share ------------------------------------------------------------
    async function shareMovie(title, url) {
        if (navigator.share) {
            try {
                await navigator.share({ title, url });
                return;
            } catch (err) {
                return; // User cancelled the native share sheet.
            }
        }
        try {
            await navigator.clipboard.writeText(url);
            toast("Link copied to clipboard", "success");
        } catch (err) {
            toast(url, "info");
        }
    }

    // Links marked data-coming-soon (nav items for features that
    // genuinely don't exist yet) give honest feedback instead of
    // silently doing nothing when clicked.
    document.addEventListener("click", (event) => {
        const link = event.target.closest("[data-coming-soon]");
        if (!link) return;
        event.preventDefault();
        toast(link.dataset.comingSoon, "info");
    });

    document.addEventListener("DOMContentLoaded", () => {
        if (isAuthenticated()) {
            const params = new URLSearchParams(window.location.search);
            const initialLoad = params.has("sync_favorites") ? syncGuestListToServer() : loadServerFavorites();
            initialLoad.then(() => {
                if (params.has("sync_favorites")) {
                    params.delete("sync_favorites");
                    const newQuery = params.toString();
                    history.replaceState(null, "", window.location.pathname + (newQuery ? `?${newQuery}` : ""));
                }
            });
        } else {
            refreshMyListButtons();
        }
    });

    return {
        toast,
        escapeHTML,
        isAuthenticated,
        getMyList,
        isInMyList,
        toggleMyList,
        refreshMyListButtons,
        loadServerFavorites,
        openTrailerModal,
        closeTrailerModal,
        shareMovie,
    };
})();
