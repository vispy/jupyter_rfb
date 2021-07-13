var widgets = require('@jupyter-widgets/base');
var _ = require('lodash');

/*
 * See widget.py for the kernel counterpart to this file.
 *
 * The server sends frames to the client, and the client sends back
 * a confirmation when it has processed the frame.
 * 
 * The client queues the frames it receives and processes them one-by-one
 * at the browser's pace, using requestAnimationFrame. We send back a
 * confirmation when the frame is processed (not when it is technically received).
 * It is the responsibility of the server to not send too many frames beyond the
 * last confirmed one.
 * 
 * When setting the img.src attribute, the browser still needs to actually render
 * the image. We wait for this before requesting a new animation. If we don't do
 * this on FF, the animation is not smooth because the image "gets stuck".
 */


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
        frame_feedback : {},
        // For the widget
        css_width : '100%',
        css_height : '300px',
        resizable : true
    }),

    initialize: function () {
        RemoteFrameBufferModel.__super__.initialize.apply(this, arguments);        
        window.rfb_model = this;  // Debug
        // Keep a list if img elements, and auto-refresh it.
        this.img_elements = [];
        window.setInterval(this.resolve_img_elements.bind(this), 1000);
         // Keep a list of frames to render
        this.frames = [];
        // We populate the above list from this callback
        this.on('msg:custom', this.on_msg, this);                
        // Initialize a stub frame
        this.last_frame = {
            src: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR42mOor68HAAL+AX6E2KOJAAAAAElFTkSuQmCC",
            index: 0,
            timestamp: 0,
        }
        // Start the animation loop
        this._img_update_pending = false;
        this._request_animation_frame();        
    },

    resolve_img_elements: async function() {
        // Here we collect img elements corresponding to the current views.
        // We also set their onload methods which we use to schedule new draws.        
        // Reset
        for (let img of this.img_elements) {
            img.onload = null;
        }
        this.img_elements = [];
        // Collect
        for (let view_id in this.views) {
            let view = await this.views[view_id];
            this.img_elements.push(view.img);
            view.img.onload = this._request_animation_frame.bind(this);
        }
        // Just in case we lose the animation loop somehow because of images dropping out.
        this._request_animation_frame();
    },

    on_msg: function(msg, buffers) {
        if (msg.type == "framebufferdata") {
            this.frames.push(msg);
        }        
    },

    _send_response: function() {
        // Let Python know what we have at the model. This prop is a dict, making it "atomic".
        let frame = this.last_frame;
        let frame_feedback = {index: frame.index, timestamp: frame.timestamp, localtime: Date.now() / 1000};
        this.set('frame_feedback', frame_feedback);
        this.save_changes();
    },

    _request_animation_frame: function () {
        // Request an animation frame, but with a tiny delay, just to avoid
        // straining the browser. This seems to actually make things more smooth.
        if (!this._img_update_pending) {
            this._img_update_pending = true;
            let func = this._animate.bind(this);
            window.setTimeout(window.requestAnimationFrame, 5, func);
        }
    },

    _animate: function() {
        this._img_update_pending = false;
        if (!this.frames.length) {
            this._request_animation_frame();
            return;
        }
        // Pick the oldest frame from the stack
        let frame = this.frames.shift();
        // Update the image sources
        for (let img of this.img_elements) {
            img.src = frame.src;
        }
        // Let the server know we processed the image (even if it's not shown yet)
        this.last_frame = frame;
        this._send_response();
        // Request a new frame. If we have images, a frame is requested *after* they load.
        if (this.img_elements.length == 0) {
            this._request_animation_frame();
        }
    },
});


var RemoteFrameBufferView = widgets.DOMWidgetView.extend({
    // Defines how the widget gets rendered into the DOM
    render: function() {
        var that = this;

        // Create image element
        this.img = new Image(1, 1);
        this.img.decoding = "sync";
        this.img.loading = "eager";
        this.img.src = this.model.last_frame.src;
        this.el.appendChild(this.img);
        
        this.model.resolve_img_elements();

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
