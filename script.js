function toggleSidebar() {
    const sidebar = document.getElementById("sidebar");

    if (sidebar) {
        sidebar.classList.toggle("open");
    }
}


function toggleNav() {
    const nav = document.getElementById("mainNav");

    if (nav) {
        nav.classList.toggle("open");
    }
}


function toggleTheme() {

    const html = document.documentElement;

    const currentTheme =
        html.dataset.theme || "light";

    const newTheme =
        currentTheme === "dark"
            ? "light"
            : "dark";

    html.dataset.theme = newTheme;

    localStorage.setItem(
        "drp-theme",
        newTheme
    );

    updateThemeIcon(newTheme);
}


function updateThemeIcon(theme) {

    const icon =
        document.getElementById("themeIcon");

    if (!icon) {
        return;
    }

    if (theme === "dark") {
        icon.textContent = "☀";
    } else {
        icon.textContent = "☾";
    }
}


document.addEventListener(
    "DOMContentLoaded",
    function () {

        const savedTheme =
            localStorage.getItem("drp-theme");

        if (savedTheme) {

            document.documentElement.dataset.theme =
                savedTheme;

            updateThemeIcon(savedTheme);
        }

    }
);