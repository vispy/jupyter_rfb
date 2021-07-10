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
        // Meta info
        _model_name : 'RemoteFrameBufferModel',
        _view_name : 'RemoteFrameBufferView',
        _model_module : 'jupyter_rfb',
        _view_module : 'jupyter_rfb',
        _model_module_version : '0.1.0',
        _view_module_version : '0.1.0',
        // For the frames
        last_index : 0,
        last_timestamp : 0.0,
        // For the widget
        css_width : '100%',
        css_height : '300px',
        resizable : true
    })
});


// Custom View. Renders the widget model.
var RemoteFrameBufferView = widgets.DOMWidgetView.extend({
    // Defines how the widget gets rendered into the DOM
    render: function() {
        var that = this;

        // Create image element
        this.img = document.createElement("img");
        this.img.src = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR42mOor68HAAL+AX6E2KOJAAAAAElFTkSuQmCC";
        this.el.appendChild(this.img);
        
        // Receive custom messages (i.e. new image data)
        this.model.on('msg:custom', this.on_msg, this);
        
        // Set of throttler functions to send events at a friendly pace
        this._throttlers = {};

        // Initialize sizing. Setting the this.el's size right now has no effect for some reason, so we use a timer.
        this.on_resizable();
        this.img.style.width = "100%";
        this.img.style.height = "100%";
        window.setTimeout(() => { this.el.style.width = this.model.get('css_width'); }, 1);
        window.setTimeout(() => { this.el.style.height = this.model.get('css_height'); }, 1);

        // Keep track of size changes from the server
        this.model.on('change:css_width', function () { this.el.style.width = this.model.get('css_width'); }, this);
        this.model.on('change:css_height', function () { this.el.style.height = this.model.get('css_height'); }, this);
        this.model.on('change:resizable', this.on_resizable, this);

        // Keep track of size changes in JS, so we can notify the server
        this._current_size = [0, 0, 1];
        this._resizeObserver = new ResizeObserver(this.check_resize.bind(that));
        this._resizeObserver.observe(this.img);
        window.addEventListener("resize", this.check_resize.bind(this));       
        
        // Prevent context menu on RMB. Firefox still shows it when shift is pressed. It seems
        // impossible to override this, so let's make this the actual behavior.
        this.img.oncontextmenu = function(e) { if (!e.shiftKey) { e.preventDefault(); e.stopPropagation(); return false; }};
        
        // Mouse events
        this.img.addEventListener('mousedown', function (e) {
            let event = create_pointer_event(that.img, e, "mouse_down");
            that.send(event);
            if (!e.altKey) { e.preventDefault(); }
        });
        this.img.addEventListener('mouseup', function (e) {
            let event = create_pointer_event(that.img, e, "mouse_up");
            that.send(event);
            if (!e.altKey) { e.preventDefault(); }
        });
        this.img.addEventListener('click', function (e) {
            let event = create_pointer_event(that.img, e, "click");
            that.send(event);
            if (!e.altKey) { e.preventDefault(); }
        });
        // TODO: mouse move
        // TODO: wheel event
        this.img.addEventListener('touchstart', function (e) {
            that.send(create_pointer_event(that.img, e, "touch_down"));
        });
        this.img.addEventListener('touchend', function (e) {
            that.send(create_pointer_event(that.img, e, "touch_up"));
        });
        this.img.addEventListener('touchcancel', function (e) {
            that.send(create_pointer_event(that.img, e, "touch_up"));
        });
        this.img.addEventListener('touchmove', function (e) {
            that.send(create_pointer_event(that.img, e, "touch_move"));
        });
    },

    on_msg: function(msg, buffers) {
        if (msg.type == "framebufferdata") {
            // Update image (it's an in-line image)
            this.img.src = msg.src;
            // Let Python know what we have at the view
            this.model.set('last_index', msg.index);
            this.model.set('last_timestamp', msg.timestamp);
            this.touch();
        }
    },

    on_resizable: function () {
        this.el.style.resize = this.model.get('resizable') ? 'both' : 'none';
    },

    check_resize: function() {
        // Called when the widget resizes. Width and height are in logical pixels.
        let w = this.img.clientWidth;
        let h = this.img.clientHeight;
        let r = window.devicePixelRatio;
        if (w == 0 && h == 0) { return; }
        if (this._current_size[0] != w || this._current_size[1] != h || this._current_size[2] != r) {
            this._current_size = [w, h, r];
            this.send_throttled({event_type: 'resize', width: w, height: h, pixel_ratio: r}, 500);
        }
    },
    
    send_throttled: function(msg, wait) {
        let event_type = msg.event_type || "";        
        let func = this._throttlers[event_type];
        if (func === undefined) {
            func = throttled(this.send, wait || 200);
            this._throttlers[event_type] = func;
        }
        func.call(this, msg);
    },

});


function throttled(func, wait) {
    var context, args, result;
    var timeout = null;
    var previous = 0;
    var later = function() {
        previous = Date.now();
        timeout = null;
        result = func.apply(context, args);
        if (!timeout) context = args = null;
    };    
    return function() {
      var now = Date.now();
      var remaining = wait - (now - previous);
      context = this;
      args = arguments;
      if (remaining <= 0 || remaining > wait) {
            if (timeout) { clearTimeout(timeout); timeout = null; }
            previous = now;
            result = func.apply(context, args);
            if (!timeout) context = args = null;
      } else if (!timeout) {
          timeout = setTimeout(later, remaining);
      }
      return result;
    };
}


function create_pointer_event(el, e, event_type) {
    let rect = el.getBoundingClientRect();
    let offset = [rect.left, rect.top];

    if (event_type.startsWith("touch")) {
        // Touch event - select one touch to represent the main position
        let t = e.changedTouches[0];
        var pos = [Number(t.clientX - offset[0]), Number(t.clientY - offset[1])];
        var page_pos = [t.pageX, t.pageY];
        var button = 0;
        var buttons = [];
        // Include basic support for multi-touch
        var touches = {};
        for (let i=0; i<e.changedTouches.length; i++) {
            let t = e.changedTouches[i];
            if (t.target !== e.target) { continue; }
            touches[t.identifier] = [Number(t.clientX - offset[0]), Number(t.clientY - offset[1]), t.force];
        }
        var ntouches = e.touches.length;
    } else {
        // Mouse event
        var pos = [Number(e.clientX - offset[0]), Number(e.clientY - offset[1])];
        var page_pos = [e.pageX, e.pageY];
        // Fix buttons
        var buttons_mask = [];
        if (e.buttons > 0) {
            buttons_mask = Array.from(e.buttons.toString(2)).reverse();
        } else if (e.which) {
            buttons_mask = [e.which.toString(2)]  // e.g. Safari (but also 1 for RMB)
        } else {
            // libjavascriptcoregtk-3.0-0  version 2.4.11-1 does not define e.buttons
            buttons_mask = [e.button.toString(2)]
        }
        var buttons = [1, 2, 3, 4, 5].filter((i) => buttons_mask[i-1] == "1");
        var button = {0: 1, 1: 3, 2: 2, 3: 4, 4: 5}[e.button];
        var touches = {'-1': [pos[0], pos[1], 1]};  // key must not clash with real touches
        var ntouches = buttons.length;
    }

    // note: our button has a value as in JS "which"
    modifiers = ["Alt", "Shift", "Ctrl", "Meta"].filter((n) => e[n.toLowerCase() + 'Key']);

    // Create event dict
    return {
        event_type: event_type,
        pos: pos,
        page_pos: page_pos,
        touches: touches,
        ntouches: ntouches,
        button: button,
        buttons: buttons,
        modifiers: modifiers,
    }
}

module.exports = {
    RemoteFrameBufferModel: RemoteFrameBufferModel,
    RemoteFrameBufferView: RemoteFrameBufferView
};
