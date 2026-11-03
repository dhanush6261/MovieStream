/**
 * api.js
 * Thin wrapper around fetch() for the /api/* endpoints.
 */

window.MovieStreamAPI = (function () {
    async function request(path, options = {}) {
        const response = await fetch(path, options);

        let data = null;

        try {
            data = await response.json();
        } catch (err) {
            data = null;
        }

        if (!response.ok) {
            const message =
                (data && data.error) ||
                `Request failed (${response.status})`;

            const error = new Error(message);
            error.status = response.status;
            error.data = data;

            throw error;
        }

        return data;
    }

    return {
        // ------------------------------------------------------------
        // MOVIES
        // ------------------------------------------------------------

        listMovies(params = {}) {
            const qs = new URLSearchParams(params).toString();

            return request(
                `/api/movies${qs ? "?" + qs : ""}`
            );
        },

        searchMovies(params = {}) {
            const qs = new URLSearchParams(params).toString();

            return request(
                `/api/movies/search${qs ? "?" + qs : ""}`
            );
        },

        getMovie(id) {
            return request(`/api/movies/${id}`);
        },

        getMoviesByIds(ids) {
            if (!ids.length) {
                return Promise.resolve({ movies: [] });
            }

            return request(
                `/api/movies?ids=${ids.join(",")}&per_page=100`
            );
        },

        updateMovie(id, fields) {
            return request(`/api/movies/${id}`, {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(fields),
            });
        },

        deleteMovie(id) {
            return request(`/api/movies/${id}`, {
                method: "DELETE",
            });
        },

        scanLibrary() {
            return request("/api/movies/scan", {
                method: "POST",
            });
        },

        listGenres() {
            return request("/api/genres");
        },

        listLanguages() {
            return request("/api/languages");
        },

        // ------------------------------------------------------------
        // FAVORITES / MY LIST
        // ------------------------------------------------------------

        getFavorites() {
            return request("/api/favorites");
        },

        addFavorite(movieId) {
            return request("/api/favorites", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    movie_id: movieId,
                }),
            });
        },

        removeFavorite(movieId) {
            return request(`/api/favorites/${movieId}`, {
                method: "DELETE",
            });
        },

        syncFavorites(movieIds) {
            return request("/api/favorites/sync", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    movie_ids: movieIds,
                }),
            });
        },

        // ------------------------------------------------------------
        // RATINGS
        // ------------------------------------------------------------

        getMovieRating(movieId) {
            return request(`/api/movies/${movieId}/rating`);
        },

        submitMovieRating(movieId, rating) {
            return request(`/api/movies/${movieId}/rating`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    rating: rating,
                }),
            });
        },

        deleteMovieRating(movieId) {
            return request(`/api/movies/${movieId}/rating`, {
                method: "DELETE",
            });
        },

        // ------------------------------------------------------------
        // WATCH HISTORY
        // ------------------------------------------------------------

        getMovieWatchHistory(movieId) {
            return request(
                `/api/movies/${movieId}/watch-history`
            );
        },

        saveMovieWatchHistory(
            movieId,
            progressSeconds,
            durationSeconds,
            completed = false
        ) {
            return request(
                `/api/movies/${movieId}/watch-history`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        progress_seconds: progressSeconds,
                        duration_seconds: durationSeconds,
                        completed: completed,
                    }),
                }
            );
        },

        getWatchHistory() {
            return request("/api/watch-history");
        },
    };
})();