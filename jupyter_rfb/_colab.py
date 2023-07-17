from .widget import RemoteFrameBuffer as RFB

try:
    from google.colab import output
    from google.colab.output._widgets import _installed_url
except ModuleNotFoundError:
    IN_COLAB = False
else:
    IN_COLAB = True

    output.enable_custom_widget_manager()
    COLAB_URL = _installed_url


def get_colab_metadata():
    """
    Returns metadata required for colab
    """
    if not IN_COLAB:
        return None

    meta = dict()
    meta["application/vnd.jupyter.widget-view+json"] = {
        "colab": {"custom_widget_manager": {"url": COLAB_URL}}
    }

    return meta


class RemoteFrameBuffer(RFB):
    def _repr_mimebundle_(self, **kwargs):
        data = super(RemoteFrameBuffer, self)._repr_mimebundle_(**kwargs)

        return data, get_colab_metadata()
