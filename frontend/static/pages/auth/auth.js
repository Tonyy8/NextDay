(function () {
    "use strict";

    function ripple(event, el) {
        var rect = el.getBoundingClientRect();
        var size = Math.max(rect.width, rect.height);
        var dot = document.createElement("span");
        dot.className = "auth-ripple";
        dot.style.width = dot.style.height = size + "px";
        dot.style.left = (event.clientX - rect.left - size / 2) + "px";
        dot.style.top = (event.clientY - rect.top - size / 2) + "px";
        el.appendChild(dot);
        dot.addEventListener("animationend", function () { dot.remove(); });
    }

    document.querySelectorAll(".auth-pressable").forEach(function (el) {
        el.addEventListener("click", function (e) {
            ripple(e, el);
        });
    });

    document.querySelectorAll(".auth-form").forEach(function (form) {
        form.addEventListener("submit", function () {
            var btn = form.querySelector(".btn-auth-primary");
            if (!btn || btn.disabled) return;
            btn.classList.add("is-loading");
            btn.disabled = true;
        });
    });
})();
