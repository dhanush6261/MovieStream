/*
 * player.js
 * Custom controls + authenticated server-side watch history.
 *
 * Watch History rules:
 *   - 0% -> 99%  : Continue Watching
 *   - 100% / ended: Completed
 *   - Completed movie opens from the beginning
 *
 * Logged-in users:
 *   - Load progress from WatchHistory API
 *   - Save progress periodically to the server
 *   - Keep localStorage as a fast local fallback
 *
 * Guests:
 *   - Continue using localStorage only
 */

(function () {
    const container = document.getElementById("player");
    const video = document.getElementById("player-video");

    if (!container || !video) return;

    const movieId = container.dataset.movieId;
    const progressKey = `moviestream_progress_${movieId}`;

    // ------------------------------------------------------------
    // Player elements
    // ------------------------------------------------------------

    const playBtn = document.getElementById("player-play");
    const skipBackBtn = document.getElementById("player-skip-back");
    const skipForwardBtn = document.getElementById("player-skip-forward");
    const muteBtn = document.getElementById("player-mute");
    const volumeSlider = document.getElementById("player-volume");
    const seekSlider = document.getElementById("player-seek");
    const timeLabel = document.getElementById("player-time");
    const speedSelect = document.getElementById("player-speed");
    const pipBtn = document.getElementById("player-pip");
    const fullscreenBtn = document.getElementById("player-fullscreen");

    const controls = document.getElementById("player-controls");
    const upNext = document.getElementById("player-up-next");
    const upNextTitle = document.getElementById("player-up-next-title");
    const upNextPlayBtn = document.getElementById("player-up-next-play");
    const upNextCancelBtn = document.getElementById("player-up-next-cancel");

    const PLAY_ICON =
        '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>';

    const PAUSE_ICON =
        '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M6 5h4v14H6zM14 5h4v14h-4z"/></svg>';

    // ------------------------------------------------------------
// Player Controls Auto-Hide
// ------------------------------------------------------------

const CONTROLS_HIDE_DELAY = 2500;

let controlsHideTimer = null;

function showPlayerControls() {
    if (!controls) {
        return;
    }

    container.classList.remove("is-controls-hidden");

    clearTimeout(controlsHideTimer);

    if (video.paused || video.ended) {
        return;
    }

    controlsHideTimer = setTimeout(() => {
        if (!video.paused && !video.ended) {
            container.classList.add("is-controls-hidden");
        }
    }, CONTROLS_HIDE_DELAY);
}

function keepPlayerControlsVisible() {
    if (!controls) {
        return;
    }

    container.classList.remove("is-controls-hidden");
    clearTimeout(controlsHideTimer);
}

container.addEventListener("mousemove", () => {
    showPlayerControls();
});

container.addEventListener(
    "touchstart",
    () => {
        showPlayerControls();
    },
    { passive: true }
);

video.addEventListener("play", () => {
    showPlayerControls();
});

video.addEventListener("pause", () => {
    keepPlayerControlsVisible();
});

video.addEventListener("ended", () => {
    keepPlayerControlsVisible();
});

controls.addEventListener("mousemove", () => {
    showPlayerControls();
});

controls.addEventListener("click", () => {
    showPlayerControls();
});

controls.addEventListener("input", () => {
    showPlayerControls();
});

controls.addEventListener("change", () => {
    showPlayerControls();
});

    // ------------------------------------------------------------
    // Watch History state
    // ------------------------------------------------------------

    let serverHistoryLoaded = false;
    let serverSaveInProgress = false;
    let lastServerSaveTime = 0;
    let progressRestoreInProgress = true;

    const SERVER_SAVE_INTERVAL = 10000; // 10 seconds

    // ------------------------------------------------------------
    // Utility
    // ------------------------------------------------------------

    function formatTime(seconds) {
        if (!isFinite(seconds) || seconds < 0) {
            seconds = 0;
        }

        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);

        return `${m}:${String(s).padStart(2, "0")}`;
    }

    // ------------------------------------------------------------
    // Play / Pause
    // ------------------------------------------------------------

    function togglePlay() {
        if (video.paused) {
            video.play().catch(() => {
                // Browser may block playback until user interaction.
            });
        } else {
            video.pause();
        }
    }

    video.addEventListener("play", () => {
        playBtn.innerHTML = PAUSE_ICON;
    });

    video.addEventListener("pause", () => {
        playBtn.innerHTML = PLAY_ICON;
        saveProgress(true);
    });

    playBtn.addEventListener("click", togglePlay);

    let lastClickTime = 0;

    video.addEventListener("click", () => {
        const now = Date.now();

        if (now - lastClickTime < 350) {
            toggleFullscreen();
        } else {
            togglePlay();
        }

        lastClickTime = now;
    });

    // ------------------------------------------------------------
    // Skip Forward / Back
    // ------------------------------------------------------------

    skipBackBtn.addEventListener("click", () => {
        video.currentTime = Math.max(
            0,
            video.currentTime - 10
        );

        saveProgress(true);
    });

    skipForwardBtn.addEventListener("click", () => {
        video.currentTime = Math.min(
            video.duration || Infinity,
            video.currentTime + 10
        );

        saveProgress(true);
    });

    // ------------------------------------------------------------
    // Seek Bar
    // ------------------------------------------------------------

    let isScrubbing = false;

let pendingResumeTime = null;
let resumeApplied = false;

async function applyResumePosition() {
    if (resumeApplied) {
        return;
    }

    if (
        pendingResumeTime === null ||
        !Number.isFinite(video.duration) ||
        video.duration <= 0
    ) {
        return;
    }

    const saved = Math.max(
        0,
        Math.min(pendingResumeTime, video.duration)
    );

    if (saved > 0 && saved < video.duration) {
        video.currentTime = saved;
        resumeApplied = true;

        seekSlider.value = saved;
        updateTimeDisplay();
    }
}

video.addEventListener("loadedmetadata", async () => {
    progressRestoreInProgress = true;

    seekSlider.max = video.duration;

    try {
        await restoreProgress();
        await applyResumePosition();
    } finally {
        progressRestoreInProgress = false;
        updateTimeDisplay();
    }
});

video.addEventListener("canplay", async () => {
    await applyResumePosition();
});

video.addEventListener("timeupdate", () => {
    if (!isScrubbing) {
        seekSlider.value = video.currentTime;
    }

    // Always keep the player time display updated.
    updateTimeDisplay();

    // Do not save progress while initial restore is running.
    if (progressRestoreInProgress) {
        return;
    }

    throttledSaveProgress();
});

function updateTimeDisplay() {
    if (
        !Number.isFinite(video.duration) ||
        video.duration <= 0
    ) {
        timeLabel.textContent = "Loading...";
        return;
    }

    timeLabel.textContent =
        `${formatTime(video.currentTime)} / ${formatTime(video.duration)}`;
}

  seekSlider.addEventListener("input", () => {
    if (
        !Number.isFinite(video.duration) ||
        video.duration <= 0
    ) {
        return;
    }

    isScrubbing = true;

    timeLabel.textContent =
        `${formatTime(Number(seekSlider.value))} / ${formatTime(video.duration)}`;
});

    seekSlider.addEventListener("change", () => {
        video.currentTime = Number(seekSlider.value);
        isScrubbing = false;

        saveProgress(true);
    });

    // ------------------------------------------------------------
    // Volume
    // ------------------------------------------------------------

    volumeSlider.addEventListener("input", () => {
        video.volume = Number(volumeSlider.value);

        video.muted = video.volume === 0;

        muteBtn.classList.toggle(
            "is-muted",
            video.muted
        );
    });

    muteBtn.addEventListener("click", () => {
        video.muted = !video.muted;

        muteBtn.classList.toggle(
            "is-muted",
            video.muted
        );

        if (!video.muted && video.volume === 0) {
            video.volume = 1;
            volumeSlider.value = 1;
        }
    });

    // ------------------------------------------------------------
    // Playback Speed
    // ------------------------------------------------------------

    speedSelect.addEventListener("change", () => {
        video.playbackRate = Number(speedSelect.value);
    });

    // ------------------------------------------------------------
    // Fullscreen
    // ------------------------------------------------------------

    function toggleFullscreen() {
        if (document.fullscreenElement) {
            document.exitFullscreen();
        } else {
            container.requestFullscreen().catch(() => {
                // Fullscreen can be denied by the browser.
            });
        }
    }

    fullscreenBtn.addEventListener(
        "click",
        toggleFullscreen
    );

    // ------------------------------------------------------------
    // Picture in Picture
    // ------------------------------------------------------------

    pipBtn.addEventListener("click", async () => {
        try {
            if (document.pictureInPictureElement) {
                await document.exitPictureInPicture();
            } else {
                await video.requestPictureInPicture();
            }
        } catch (err) {
            window.MovieStream.toast(
                "Picture-in-picture isn't supported in this browser.",
                "info"
            );
        }
    });

// ------------------------------------------------------------
// Restore Progress
// ------------------------------------------------------------

async function restoreProgress() {
    const localSaved = Number(
        localStorage.getItem(progressKey) || 0
    );

    let serverSaved = 0;
    let serverHasHistory = false;
    let completed = false;

    try {
        const history =
            await window.MovieStreamAPI.getMovieWatchHistory(
                movieId
            );

        serverHistoryLoaded = true;

        if (history) {
            completed = Boolean(history.completed);

            if (
                Number.isFinite(
                    Number(history.progress_seconds)
                )
            ) {
                serverSaved = Number(
                    history.progress_seconds
                );

                if (serverSaved > 0) {
                    serverHasHistory = true;
                }
            }
        }

        /*
         * Completed movie:
         * Open from the beginning.
         *
         * IMPORTANT:
         * Do not delete the server WatchHistory record.
         */
        if (completed) {
            video.currentTime = 0;
            localStorage.removeItem(progressKey);
            updateTimeDisplay();

            if (container.dataset.autoplay === "1") {
                video.play().catch(() => {});
            }

            return;
        }
    } catch (error) {
        serverHistoryLoaded = false;
    }

    let saved = 0;

    /*
     * Server history is preferred.
     * localStorage is the fallback.
     */
    if (serverHasHistory) {
        saved = serverSaved;
    } else {
        saved = localSaved;
    }

    if (
        Number.isFinite(video.duration) &&
        video.duration > 0
    ) {
        saved = Math.max(
            0,
            Math.min(saved, video.duration)
        );
    }

    /*
 * Store the exact saved position.
 *
 * We apply it later when video.duration is definitely ready.
 * This fixes hard-refresh resume issues.
 */
if (saved > 0) {
    pendingResumeTime = saved;
    await applyResumePosition();
}

    if (saved > 0) {
        localStorage.setItem(
            progressKey,
            String(saved)
        );
    }

    if (container.dataset.autoplay === "1") {
        video.play().catch(() => {});
    }
}


    // ------------------------------------------------------------
    // Save Progress
    // ------------------------------------------------------------

    function throttledSaveProgress() {
        const now = Date.now();

        if (
            now - lastServerSaveTime >=
            SERVER_SAVE_INTERVAL
        ) {
            saveProgress(false);
            lastServerSaveTime = now;
        }
    }

    async function saveProgress(
        forceServerSave = false,
        completedOverride = false
    ) {
        // Do not save the initial 0-second position
        // while Watch History is being restored.
    if (progressRestoreInProgress) {
        return;
    }

        if (
            !Number.isFinite(video.currentTime) ||
            video.currentTime < 0
        ) {
            return;
        }

        const currentTime = video.currentTime;
        const duration = video.duration;

        // Always keep localStorage working.
        localStorage.setItem(
            progressKey,
            String(currentTime)
        );

        // Don't send server requests until metadata is available.
        if (
            !Number.isFinite(duration) ||
            duration <= 0
        ) {
            return;
        }

        // Prevent saving during initial resume restoration.
        if (progressRestoreInProgress) {
            return;
        }

        // Prevent overlapping requests.
        if (serverSaveInProgress) {
            return;
        }

        // Server save is useful for authenticated users.
        if (!forceServerSave && !serverHistoryLoaded) {
            return;
        }

        // --------------------------------------------------------
        // IMPORTANT:
        // DO NOT use 95% as completed.
        //
        // Only the actual "ended" event sends completed=true.
        // --------------------------------------------------------

        const completed = completedOverride;

        serverSaveInProgress = true;

        try {
            await window.MovieStreamAPI.saveMovieWatchHistory(
                movieId,
                currentTime,
                duration,
                completed
            );
        } catch (error) {
            // Guest users and temporary network failures
            // continue using localStorage.
        } finally {
            serverSaveInProgress = false;
        }
    }

    
    // ------------------------------------------------------------
    // Save when leaving the page
    // ------------------------------------------------------------

function saveProgressSafely() {
    // Never overwrite a valid saved position with 0
    // during refresh/navigation.
    if (
        !Number.isFinite(video.currentTime) ||
        video.currentTime <= 0
    ) {
        return;
    }

    saveProgress(true);
}

window.addEventListener(
    "beforeunload",
    () => {
        saveProgressSafely();
    }
);

// Also save when the page becomes hidden.
document.addEventListener(
    "visibilitychange",
    () => {
        if (document.visibilityState === "hidden") {
            saveProgressSafely();
        }
    }
);
    // ------------------------------------------------------------
    // Keyboard Shortcuts
    // ------------------------------------------------------------

    document.addEventListener("keydown", (event) => {
        const tag =
            document.activeElement &&
            document.activeElement.tagName;

        if (
            tag === "INPUT" ||
            tag === "TEXTAREA" ||
            tag === "SELECT"
        ) {
            return;
        }

        switch (event.key) {
            case " ":
                event.preventDefault();
                togglePlay();
                break;

            case "ArrowRight":
                video.currentTime = Math.min(
                    video.duration || Infinity,
                    video.currentTime + 10
                );
                saveProgress(true);
                break;

            case "ArrowLeft":
                video.currentTime = Math.max(
                    0,
                    video.currentTime - 10
                );
                saveProgress(true);
                break;

            case "ArrowUp":
                event.preventDefault();

                video.volume = Math.min(
                    1,
                    video.volume + 0.1
                );

                volumeSlider.value =
                    video.volume;

                break;

            case "ArrowDown":
                event.preventDefault();

                video.volume = Math.max(
                    0,
                    video.volume - 0.1
                );

                volumeSlider.value =
                    video.volume;

                break;

            case "m":
            case "M":
                video.muted = !video.muted;

                muteBtn.classList.toggle(
                    "is-muted",
                    video.muted
                );

                break;

            case "f":
            case "F":
                toggleFullscreen();
                break;
        }
    });

    // ------------------------------------------------------------
    // Auto Continue / Actual Completion
    // ------------------------------------------------------------

    video.addEventListener("ended", async () => {
        // --------------------------------------------------------
        // IMPORTANT:
        // This is the ONLY place where completed=true is sent.
        // --------------------------------------------------------

        await saveProgress(true, true);

        // Movie is genuinely complete.
        // Remove local resume position.
        localStorage.removeItem(progressKey);

        // Keep Continue Watching behavior controlled by server.
        // Do NOT remove WatchHistory here.

        if (!container.dataset.nextUrl) {
            return;
        }

        upNextTitle.textContent =
            container.dataset.nextTitle;

        upNext.hidden = false;

        const autoTimer = setTimeout(() => {
            window.location.href =
                container.dataset.nextUrl +
                "?autoplay=1";
        }, 8000);

        upNextPlayBtn.addEventListener(
            "click",
            () => {
                clearTimeout(autoTimer);

                window.location.href =
                    container.dataset.nextUrl +
                    "?autoplay=1";
            },
            { once: true }
        );

        upNextCancelBtn.addEventListener(
            "click",
            () => {
                clearTimeout(autoTimer);
                upNext.hidden = true;
            },
            { once: true }
        );
    });
})();