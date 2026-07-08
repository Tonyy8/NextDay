FONT_SIZES = ("sm", "md", "lg")
UI_LANGS = ("th", "en")

SESSION_FONT_SIZE = "font_size"
SESSION_UI_LANG = "ui_lang"


def get_font_size(request):
    value = request.session.get(SESSION_FONT_SIZE, "md")
    return value if value in FONT_SIZES else "md"


def get_ui_lang(request):
    value = request.session.get(SESSION_UI_LANG, "th")
    return value if value in UI_LANGS else "th"


def set_font_size(request, value):
    if value in FONT_SIZES:
        request.session[SESSION_FONT_SIZE] = value


def set_ui_lang(request, value):
    if value in UI_LANGS:
        request.session[SESSION_UI_LANG] = value
