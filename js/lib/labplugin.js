var plugin = require('./index');
var base = require('@jupyter-widgets/base');

module.exports = {
  id: 'jupyter_rfb:plugin',
  requires: [base.IJupyterWidgetRegistry],
  activate: function(app, widgets) {
      widgets.registerWidget({
          name: 'jupyter_rfb',
          version: plugin.version,
          exports: plugin
      });
  },
  autoStart: true
};

