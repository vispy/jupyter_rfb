try:
    # determine if running in colab
    from google.colab import output
except Exception:
    IN_COLAB = False
    COLAB_URL = None
else:
    IN_COLAB = True
    # useful to enable widget manager here so the user doesn't have to manually
    output.enable_custom_widget_manager()


def get_colab_metadata():
    """
    Get the metadata required for running in a colab notebook.

    Returns ``None` if not running in a colab notebook.
    """

    if not IN_COLAB:
        return None
    from google.colab.output._widgets import _installed_url as COLAB_URL
    meta = dict()
    meta["application/vnd.jupyter.widget-view+json"] = {
        "colab": {"custom_widget_manager": {"url": COLAB_URL}}
    }

    return meta
