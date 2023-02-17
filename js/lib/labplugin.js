import {RemoteFrameBufferModel, RemoteFrameBufferView, version} from './index';
import {IJupyterWidgetRegistry} from '@jupyter-widgets/base';

export const remoteFrameBufferPlugin = {
  id: 'jupyter_rfb:plugin',
  requires: [IJupyterWidgetRegistry],
  activate: function(app, widgets) {
      widgets.registerWidget({
          name: 'jupyter_rfb',
          version: version,
          exports: { RemoteFrameBufferModel, RemoteFrameBufferView }
      });
  },
  autoStart: true
};

export default remoteFrameBufferPlugin;