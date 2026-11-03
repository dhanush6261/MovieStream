/**
 * navbar.js
 * - Adds .scrolled to the navbar once the page scrolls past the hero.
 * - Toggles the mobile nav menu open/closed.
 * - Dark/light theme toggle, persisted in localStorage (applied
 *   before first paint by the inline script in base.html; this file
 *   just handles the button click and keeping its icon in sync).
 * - Notifications dropdown (click to open/close).
 * - Profile dropdown: works via CSS :hover already, but also toggles
 *   on click so it's reliable on trackpads/touch, not just mouse hover.
 */

(function () {
    const navbar = document.getElementById("navbar");
    const mobileToggle = document.getElementById("navbar-mobile-toggle");
    const mobileLinks = document.getElementById("navbar-mobile-links");

    function handleScroll() {
        if (!navbar) return;
        if (window.scrollY > 40) {
            navbar.classList.add("scrolled");
        } else {
            navbar.classList.remove("scrolled");
        }
    }

    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll(); // Set correct state on initial load (e.g. after a refresh mid-scroll).

    if (mobileToggle && mobileLinks) {
        mobileToggle.addEventListener("click", () => {
            mobileLinks.classList.toggle("open");
            mobileToggle.classList.toggle("open");
        });
    }

    // --- Dark / light theme toggle -----------------------------------------
    const THEME_KEY = "moviestream_theme";
    const themeToggle = document.getElementById("dark-mode-toggle");

    function currentTheme() {
        return document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
    }

    function applyThemeIcon() {
        if (!themeToggle) return;
        const isLight = currentTheme() === "light";
        themeToggle.classList.toggle("is-active", isLight);
        themeToggle.setAttribute("aria-pressed", String(isLight));
        themeToggle.title = isLight ? "Switch to dark mode" : "Switch to light mode";
    }

    if (themeToggle) {
        applyThemeIcon();
        themeToggle.addEventListener("click", () => {
            const next = currentTheme() === "light" ? "dark" : "light";
            if (next === "light") {
                document.documentElement.setAttribute("data-theme", "light");
            } else {
                document.documentElement.removeAttribute("data-theme");
            }
            localStorage.setItem(THEME_KEY, next);
            applyThemeIcon();
        });
    }

    // --- Notifications dropdown ---------------------------------------------
    const notifBtn = document.querySelector('[aria-label="Notifications"]');
    if (notifBtn) {
        let panel = null;

        function closeNotifications() {
            if (panel) {
                panel.remove();
                panel = null;
            }
            document.removeEventListener("click", handleOutsideClick);
        }

        function handleOutsideClick(event) {
            if (panel && !panel.contains(event.target) && event.target !== notifBtn) {
                closeNotifications();
            }
        }

        notifBtn.addEventListener("click", (event) => {
            event.stopPropagation();
            if (panel) {
                closeNotifications();
                return;
            }
            panel = document.createElement("div");
            panel.className = "navbar-notif-panel";
            panel.innerHTML = `
                <p class="navbar-notif-title">Notifications</p>
                <p class="navbar-notif-empty">You're all caught up - no new notifications yet.</p>
            `;
            notifBtn.parentElement.style.position = "relative";
            notifBtn.parentElement.appendChild(panel);
            document.addEventListener("click", handleOutsideClick);
        });
    }

    // --- Profile dropdown: click as well as hover ----------------------------
    const userMenu = document.querySelector(".navbar-user-menu");
    if (userMenu) {
        const dropdown = userMenu.querySelector(".navbar-user-dropdown");
        const avatarLink = userMenu.querySelector(".navbar-avatar");

        if (dropdown && avatarLink) {
            avatarLink.addEventListener("click", (event) => {
                // Small screens / first tap: open the dropdown instead of
                // immediately navigating, so Edit Profile/Logout are reachable
                // without relying on hover. A second click on the (now-open)
                // link still navigates to the profile page normally.
                if (!dropdown.classList.contains("force-open")) {
                    event.preventDefault();
                    dropdown.classList.add("force-open");
                    document.addEventListener(
                        "click",
                        function closeDropdown(e) {
                            if (!userMenu.contains(e.target)) {
                                dropdown.classList.remove("force-open");
                                document.removeEventListener("click", closeDropdown);
                            }
                        }
                    );
                }
            });
        }
    }
})();
