var widgets = require('@jupyter-widgets/base');
var _ = require('lodash');

// See widget.py for the kernel counterpart to this file.


// Custom Model. Custom widgets models must at least provide default values
// for model attributes, including
//
//  - `_view_name`
//  - `_view_module`
//  - `_view_module_version`
//
//  - `_model_name`
//  - `_model_module`
//  - `_model_module_version`
//
//  when different from the base class.

// When serialiazing the entire widget state for embedding, only values that
// differ from the defaults will be specified.
var RemoteFrameBufferModel = widgets.DOMWidgetModel.extend({
    defaults: _.extend(widgets.DOMWidgetModel.prototype.defaults(), {
        _model_name : 'RemoteFrameBufferModel',
        _view_name : 'RemoteFrameBufferView',
        _model_module : 'jupyterfb',
        _view_module : 'jupyterfb',
        _model_module_version : '0.1.0',
        _view_module_version : '0.1.0',
        value : 'Hello World!'
    })
});


// Custom View. Renders the widget model.
var RemoteFrameBufferView = widgets.DOMWidgetView.extend({
    // Defines how the widget gets rendered into the DOM
    render: function() {
        this.value_changed();

        // Observe changes in the value traitlet in Python, and define
        // a custom callback.
        this.model.on('change:value', this.value_changed, this);
    },

    value_changed: function() {
        this.el.textContent = this.model.get('value');
    }
});


module.exports = {
    RemoteFrameBufferModel: RemoteFrameBufferModel,
    RemoteFrameBufferView: RemoteFrameBufferView
};
