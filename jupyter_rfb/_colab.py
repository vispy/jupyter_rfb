try:
    # determine if running in colab
    from google.colab import output
    from google.colab.output._widgets import _installed_url
except Exception:
    IN_COLAB = False
    COLAB_URL = None
else:
    IN_COLAB = True
    # useful to enable widget manager here so the user doesn't have to manually
    output.enable_custom_widget_manager()
    # the metadata that colab needs
    COLAB_URL = _installed_url


def get_colab_metadata():
    """
    Gets metadata required for colab notebooks. Returns ``None` if not running in a colab notebook.
    """

    if not IN_COLAB:
        return None

    meta = dict()
    meta["application/vnd.jupyter.widget-view+json"] = {
        "colab": {"custom_widget_manager": {"url": COLAB_URL}}
    }

    return meta
