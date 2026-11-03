/**
 * horizontal-scroll.js
 * Makes every .movie-row-scroller behave like Netflix's rows:
 *   - Shift + mouse wheel scrolls the row horizontally (the standard
 *     OS convention). Plain vertical wheel/trackpad scroll is left
 *     alone so it always scrolls the PAGE, even when the cursor
 *     happens to be over a row -- hijacking it unconditionally was
 *     the bug that made page scrolling randomly stop working.
 *   - Native trackpad horizontal swipes (deltaX-dominant) already
 *     scroll the row correctly without any help from us.
 *   - Click-and-drag (mouse) pans the row.
 *   - Left/Right arrow keys move by one card width when a card
 *     inside the row has focus (keyboard accessibility).
 */

(function () {
    const scrollers = document.querySelectorAll(".movie-row-scroller");

    // Shared drag state so we only need one pair of window-level
    // mousemove/mouseup listeners total, not one pair per row.
    let dragTarget = null;
    let dragStartX = 0;
    let dragStartScrollLeft = 0;

    window.addEventListener("mouseup", () => {
        if (dragTarget) dragTarget.style.cursor = "";
        dragTarget = null;
    });

    window.addEventListener("mousemove", (event) => {
        if (!dragTarget) return;
        const delta = event.pageX - dragStartX;
        dragTarget.scrollLeft = dragStartScrollLeft - delta;
    });

    scrollers.forEach((scroller) => {
        // --- Wheel: Shift+wheel scrolls horizontally; plain wheel doesn't ---
        scroller.addEventListener(
            "wheel",
            (event) => {
                // Native horizontal trackpad swipe: let the browser handle it.
                if (Math.abs(event.deltaX) >= Math.abs(event.deltaY)) return;
                // Plain vertical scroll: let it bubble up and scroll the page.
                if (!event.shiftKey) return;

                event.preventDefault();
                scroller.scrollLeft += event.deltaY;
            },
            { passive: false }
        );

        // --- Drag to scroll (mouse) -----------------------------------
        scroller.addEventListener("mousedown", (event) => {
            dragTarget = scroller;
            dragStartX = event.pageX;
            dragStartScrollLeft = scroller.scrollLeft;
            scroller.style.cursor = "grabbing";
        });

        // --- Keyboard: move by one card when a card is focused ----------
        scroller.addEventListener("keydown", (event) => {
            const card = event.target.closest(".movie-card");
            if (!card) return;

            if (event.key === "ArrowRight") {
                event.preventDefault();
                scroller.scrollBy({ left: card.offsetWidth + 16, behavior: "smooth" });
            } else if (event.key === "ArrowLeft") {
                event.preventDefault();
                scroller.scrollBy({ left: -(card.offsetWidth + 16), behavior: "smooth" });
            }
        });
    });
})();
