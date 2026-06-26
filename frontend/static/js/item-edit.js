(function () {
    function initColorPickers(root) {
        root = root || document;
        root.querySelectorAll(".color-picker").forEach(function (picker) {
            var input = document.getElementById(picker.dataset.colorInput);
            var label = picker.dataset.colorLabel
                ? document.getElementById(picker.dataset.colorLabel)
                : null;
            var btns = picker.querySelectorAll(".color-swatch-btn");

            function highlight(hex) {
                btns.forEach(function (b) {
                    var on = hex && b.dataset.hex.toLowerCase() === hex.toLowerCase();
                    b.classList.toggle("is-selected", on);
                    if (on && label) label.textContent = b.dataset.name;
                });
            }

            if (!picker.dataset.bound) {
                picker.dataset.bound = "1";
                btns.forEach(function (btn) {
                    btn.addEventListener("click", function () {
                        if (input) input.value = btn.dataset.hex;
                        highlight(btn.dataset.hex);
                    });
                });
            }

            highlight(input ? input.value : "");
        });
    }

    window.initColorPickers = initColorPickers;

    document.addEventListener("DOMContentLoaded", function () {
        initColorPickers(document);
    });
})();
