(function () {
    "use strict";

    var STORAGE_FONT = "nd_font_size";
    var STORAGE_LANG = "nd_ui_lang";

    function getCookie(name) {
        var match = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
        return match ? decodeURIComponent(match[1]) : "";
    }

    function applyFontSize(size) {
        var html = document.documentElement;
        html.classList.remove("font-sm", "font-md", "font-lg");
        html.classList.add("font-" + (size || "md"));
    }

    function applyLanguage(lang) {
        var dict = window.ND_I18N && window.ND_I18N[lang];
        if (!dict) return;
        document.documentElement.lang = lang;
        document.documentElement.classList.remove("lang-th", "lang-en");
        document.documentElement.classList.add("lang-" + lang);
        document.querySelectorAll("[data-i18n]").forEach(function (el) {
            var key = el.getAttribute("data-i18n");
            if (dict[key]) {
                if (el.tagName === "INPUT" || el.tagName === "TEXTAREA") {
                    el.placeholder = dict[key];
                } else {
                    el.textContent = dict[key];
                }
            }
        });
        document.querySelectorAll("[data-i18n-title]").forEach(function (el) {
            var key = el.getAttribute("data-i18n-title");
            if (dict[key]) el.setAttribute("title", dict[key]);
        });
        document.querySelectorAll("[data-i18n-aria]").forEach(function (el) {
            var key = el.getAttribute("data-i18n-aria");
            if (dict[key]) el.setAttribute("aria-label", dict[key]);
        });
    }

    function applyAll(fontSize, lang) {
        applyFontSize(fontSize);
        applyLanguage(lang);
    }

    function savePreference(name, value) {
        var body = new URLSearchParams();
        body.set(name, value);
        body.set("csrfmiddlewaretoken", getCookie("csrftoken"));

        var saveUrl = document.body && document.body.dataset.settingsUrl;
        if (!saveUrl) return Promise.resolve();

        return fetch(saveUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Requested-With": "XMLHttpRequest",
            },
            body: body.toString(),
        }).catch(function () { /* offline / mock — local still works */ });
    }

    function setFontSize(size) {
        if (!size) return;
        localStorage.setItem(STORAGE_FONT, size);
        applyFontSize(size);
        savePreference("font_size", size);
        document.querySelectorAll('input[name="font_size"]').forEach(function (input) {
            input.checked = input.value === size;
        });
        document.querySelectorAll("[data-font-option]").forEach(function (btn) {
            btn.classList.toggle("is-active", btn.dataset.fontOption === size);
        });
    }

    function setLanguage(lang) {
        if (!lang) return;
        localStorage.setItem(STORAGE_LANG, lang);
        applyLanguage(lang);
        savePreference("ui_lang", lang);
        document.querySelectorAll('input[name="ui_lang"]').forEach(function (input) {
            input.checked = input.value === lang;
        });
        document.querySelectorAll("[data-lang-option]").forEach(function (btn) {
            btn.classList.toggle("is-active", btn.dataset.langOption === lang);
        });
    }

    function initFromStorage() {
        var html = document.documentElement;
        var fontSize = localStorage.getItem(STORAGE_FONT) || html.dataset.fontSize || "md";
        var lang = localStorage.getItem(STORAGE_LANG) || html.dataset.uiLang || "th";
        applyAll(fontSize, lang);
        return { fontSize: fontSize, lang: lang };
    }

    function bindSettingsPage() {
        document.querySelectorAll("[data-font-option]").forEach(function (btn) {
            btn.addEventListener("click", function () {
                setFontSize(btn.dataset.fontOption);
                flashSaved();
            });
        });
        document.querySelectorAll("[data-lang-option]").forEach(function (btn) {
            btn.addEventListener("click", function () {
                setLanguage(btn.dataset.langOption);
                flashSaved();
            });
        });
    }

    function flashSaved() {
        var badge = document.getElementById("settings-saved");
        if (!badge) return;
        badge.hidden = false;
        badge.classList.add("show");
        clearTimeout(flashSaved._t);
        flashSaved._t = setTimeout(function () {
            badge.classList.remove("show");
            badge.hidden = true;
        }, 1800);
    }

    window.NDSettings = {
        applyAll: applyAll,
        setFontSize: setFontSize,
        setLanguage: setLanguage,
        init: initFromStorage,
    };

    document.addEventListener("DOMContentLoaded", function () {
        var prefs = initFromStorage();
        bindSettingsPage();
        document.querySelectorAll("[data-font-option]").forEach(function (btn) {
            btn.classList.toggle("is-active", btn.dataset.fontOption === prefs.fontSize);
        });
        document.querySelectorAll("[data-lang-option]").forEach(function (btn) {
            btn.classList.toggle("is-active", btn.dataset.langOption === prefs.lang);
        });
    });
})();
