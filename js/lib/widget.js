import { DOMWidgetModel, DOMWidgetView } from '@jupyter-widgets/base';

/*
* For the kernel counterpart to this file, see widget.py
* For the base class, see https://github.com/jupyter-widgets/ipywidgets/blob/master/packages/base/src/widget.ts
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

export const version = "0.5.1";

export class RemoteFrameBufferModel extends DOMWidgetModel {
    defaults() {
        return {
            ...super.defaults(),
            _model_name: 'RemoteFrameBufferModel',
            _view_name: 'RemoteFrameBufferView',
            _model_module: 'jupyter_rfb',
            _view_module: 'jupyter_rfb',
            _model_module_version: version,
            _view_module_version: version,
            // For the frames
            frame_feedback: {},
            // For the widget
            css_width: '500px',
            css_height: '300px',
            resizable: true,
            has_visible_views: false,
            cursor: 'default'
        };
    }
    initialize() {
        super.initialize.apply(this, arguments);
        // Keep a list if img elements.
        this.img_elements = [];
        // Observer that will check whether the img elements are within the viewport.
        this._intersection_observer = new IntersectionObserver(this._intersection_callback.bind(this));
        // We update the img element list (and the intersection observer) automatically when
        // a new view is added or removed. But this (especially the latter) may not work in
        // all possible cases. So let's also call it on a low interval.
        window.setInterval(this.collect_view_img_elements.bind(this), 5000);
        // Keep a list of frames to render.
        this.frames = [];
        // We populate the above list from this callback.
        this.on('msg:custom', this.on_msg, this);
        // Initialize a stub frame.
        this.last_frame = {
            src: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR42mOor68HAAL+AX6E2KOJAAAAAElFTkSuQmCC',
            index: 0,
            timestamp: 0,
        };
        // Start the animation loop
        this._img_update_pending = false;
        this._request_animation_frame();
    }

    async collect_view_img_elements() {
        // Here we collect img elements corresponding to the current views.
        // We also set their onload methods which we use to schedule new draws.
        // Plus we reset out visibility obserer.
        this._intersection_observer.disconnect();
        // Reset
        for (let img of this.img_elements) {
            img.onload = null;
        }
        this.img_elements = [];
        // Collect
        for (let view_id in this.views) {
            let view = await this.views[view_id];
            this._intersection_observer.observe(view.img);
            this.img_elements.push(view.img);
            view.img.onload = this._request_animation_frame.bind(this);
        }
        // Just in case we lose the animation loop somehow because of images dropping out.
        this._request_animation_frame();
    }

    /**
     * @param {Object} msg
     * @param {DataView[]} buffers
     */
    on_msg(msg, buffers) {
        if (msg.type === 'framebufferdata') {
            this.frames.push({ ...msg, buffers: buffers });
        }
    }

    _intersection_callback(entries, observer) {
        // This gets called when one of the views becomes visible/invisible.
        // Note that entries only contains the *changed* elements.

        // Set visibility of changed img elements.
        for (let entry of entries) {
            entry.target._is_visible = entry.isIntersecting;
        }
        // Now count how many are visible
        let count = 0;
        for (let img of this.img_elements) {
            if (img._is_visible) { count += 1; }
        }
        // If the state changed, update our flag
        let has_visible_views = count > 0;
        if (has_visible_views != this.get("has_visible_views")) {
            this.set('has_visible_views', has_visible_views);
            this.save_changes();
        }
    }

    _send_response() {
        // Let Python know what we have at the model. This prop is a dict, making it "atomic".
        let frame = this.last_frame;
        let frame_feedback = { index: frame.index, timestamp: frame.timestamp, localtime: Date.now() / 1000 };
        this.set('frame_feedback', frame_feedback);
        this.save_changes();
    }

    _request_animation_frame() {
        // Request an animation frame, but with a tiny delay, just to avoid
        // straining the browser. This seems to actually make things more smooth.
        if (!this._img_update_pending) {
            this._img_update_pending = true;
            let func = this._animate.bind(this);
            window.setTimeout(window.requestAnimationFrame, 5, func);
        }
    }

    _animate() {
        this._img_update_pending = false;
        if (!this.frames.length) {
            this._request_animation_frame();
            return;
        }
        // Pick the oldest frame from the stack
        let frame = this.frames.shift();
        let new_src;
        if (frame.buffers.length > 0) {
            let blob = new Blob([frame.buffers[0].buffer], { type: frame.mimetype });
            new_src = URL.createObjectURL(blob);
        } else {
            new_src = frame.data_b64;
        }
        let old_src = this.img_elements?.[0]?.src;
        if (old_src.startsWith('blob:')) { URL.revokeObjectURL(old_src); }
        // Update the image sources
        for (let img of this.img_elements) {
            img.src = new_src;
        }
        // Let the server know we processed the image (even if it's not shown yet)
        this.last_frame = frame;
        this._send_response();
        // Request a new frame. If we have images, a frame is requested *after* they load.
        if (this.img_elements.length === 0) {
            this._request_animation_frame();
        }
    }

    close() {
        // This gets called when model is closed and the comm is removed. Notify Py just in time!
        this.send({ event_type: 'close', time_stamp: get_time_stamp() }); // does nothing if this.comm is already gone
        super.close.apply(this, arguments);
    }
}


export class RemoteFrameBufferView extends DOMWidgetView {
    // Defines how the widget gets rendered into the DOM
    render() {
        var that = this;

        // Create a stub element that can grab focus
        this.focus_el = document.createElement("a");
        this.focus_el.href = "#";
        this.focus_el.style.position = "absolute";
        this.focus_el.style.width = "1px";
        this.focus_el.style.height = "1px";
        this.focus_el.style.padding = "0";
        this.focus_el.style.zIndex = "-99";
        this.el.appendChild(this.focus_el);

        // Create image element
        this.img = new Image();
        // Tweak loading behavior. These should be the defaults, but we set them just in case.
        this.img.decoding = 'sync';
        this.img.loading = 'eager';
        // Tweak mouse/touch/pointer/key behavior
        this.img.style.touchAction = 'none'; // prevent default pan/zoom behavior
        this.img.ondragstart = () => false; // prevent browser's built-in image drag
        this.img.tabIndex = -1;
        // Prevent context menu on RMB. Firefox still shows it when shift is pressed. It seems
        // impossible to override this (tips welcome!), so let's make this the actual behavior.
        this.img.oncontextmenu = function (e) { if (!e.shiftKey) { e.preventDefault(); e.stopPropagation(); return false; } };

        // Initialize the image
        this.img.src = this.model.last_frame.src;
        this.el.appendChild(this.img);
        this.model.collect_view_img_elements();

        // Cursor
        this.el.style.cursor = this.model.get('cursor');
        this.model.on('change:cursor', function () { this.el.style.cursor = this.model.get('cursor'); }, this);

        // Set of throttler functions to send events at a friendly pace
        this._throttlers = {};

        // Initialize sizing.
        // Setting the this.el's size right now has no effect. We also set it in _check_size() below.
        this.img.style.width = '100%';
        this.img.style.height = '100%';
        this.el.style.width = this.model.get('css_width');
        this.el.style.height = this.model.get('css_height');
        this.el.style.resize = this.model.get('resizable') ? 'both' : 'none';
        this.el.style.overflow = 'hidden';  // resize does not work if overflow is 'visible'

        // Keep track of size changes from the server
        this.model.on('change:css_width', function () { this.el.style.width = this.model.get('css_width'); }, this);
        this.model.on('change:css_height', function () { this.el.style.height = this.model.get('css_height'); }, this);
        this.model.on('change:resizable', function () { this.el.style.resize = this.model.get('resizable') ? 'both' : 'none'; }, this);

        // Keep track of size changes in JS, so we can notify the server
        this._current_size = [0, 0, 1];
        this._resizeObserver = new ResizeObserver(this._check_resize.bind(that));
        this._resizeObserver.observe(this.img);
        window.addEventListener('resize', this._check_resize.bind(this));

        // Pointer events
        this._pointers = {};
        this._last_buttons = [];
        this.img.addEventListener('pointerdown', function (e) {
            // This is what makes the JS PointerEvent so great. We can enable mouse capturing
            // and we will receive mouse-move and mouse-up even when the pointer moves outside
            // the element. Best of all, the capturing is disabled automatically!
            that.focus_el.focus({ preventScroll: true, focusVisble: false });
            that.img.setPointerCapture(e.pointerId);
            that._pointers[e.pointerId] = e;
            let event = create_pointer_event(that.img, e, that._pointers, 'pointer_down');
            that._last_buttons = event.buttons;
            that.send(event);
            if (!e.altKey) { e.preventDefault(); }
        });
        this.img.addEventListener('lostpointercapture', function (e) {
            // This happens on pointer-up or pointer-cancel. We threat them the same.
            // The event we emit will still include the touch hat goes up.
            let event = create_pointer_event(that.img, e, that._pointers, 'pointer_up');
            delete that._pointers[e.pointerId];
            that._last_buttons = event.buttons;
            that.send(event);
        });
        this.img.addEventListener('pointermove', function (e) {
            // If this pointer is not down, but other pointers are, don't emit an event.
            if (that._pointers[e.pointerId] === undefined) {
                if (Object.keys(that._pointers).length > 0) { return; }
            }
            let event = create_pointer_event(that.img, e, that._pointers, 'pointer_move');
            that.send_throttled(event, 20);
        });

        // Click events are not pointer events. Not sure if we need click events. It seems to make
        // less sense, because the img is just a single element. Only double-click for now.
        this.img.addEventListener('dblclick', function (e) {
            let event = create_pointer_event(that.img, e, {}, 'double_click');
            delete event.touches;
            delete event.ntouches;
            that.send(event);
            if (!e.altKey) { e.preventDefault(); }
        });

        // Scrolling. Need a special throttling that accumulates the deltas.
        // Also, only consume the wheel event when we have focus.
        // On Firefox, e.buttons is always 0 for wheel events, so we use a cached value for the buttons.
        this._wheel_state = { dx: 0, dy: 0, e: null, pending: false };
        function send_wheel_event() {
            let e = that._wheel_state.e;
            let rect = that.img.getBoundingClientRect();
            let event = {
                event_type: 'wheel',
                x: Number(e.clientX - rect.left),
                y: Number(e.clientY - rect.top),
                dx: that._wheel_state.dx,
                dy: that._wheel_state.dy,
                buttons: that._last_buttons,
                modifiers: get_modifiers(e),
                time_stamp: get_time_stamp(),
            };
            that._wheel_state.dx = 0;
            that._wheel_state.dy = 0;
            that._wheel_state.pending = false;
            that.send(event);
        }
        this.img.addEventListener('wheel', function (e) {
            if (window.document.activeElement !== that.focus_el) { return; }
            let scales = [1 / window.devicePixelRatio, 16, 600];  // pixel, line, page
            let scale = scales[e.deltaMode];
            that._wheel_state.dx += e.deltaX * scale;
            that._wheel_state.dy += e.deltaY * scale;
            if (!that._wheel_state.pending) {
                that._wheel_state.pending = true;
                that._wheel_state.e = e;
                window.setTimeout(send_wheel_event, 20);
            }
            if (!e.altKey) { e.preventDefault(); }
        });

        // Key events - approach inspired from ipyevents
        function key_event_handler(e) {
            // Failsafe in case the element is deleted or detached.
            if (that.el.offsetParent === null) { return; }
            let event = {
                event_type: 'key_' + e.type.slice(3),
                key: KEYMAP[e.key] || e.key,
                modifiers: get_modifiers(e),
                time_stamp: get_time_stamp(),
            };
            if (!e.repeat) { that.send(event); } // dont do the sticky key thing
            e.stopPropagation();
            e.preventDefault();
        }
        this.focus_el.addEventListener('keydown', key_event_handler, true);
        this.focus_el.addEventListener('keyup', key_event_handler, true);
    }

    remove() {
        // This gets called when the view is removed from the DOM. There can still be other views though!
        super.remove.apply(this, arguments);
        window.setTimeout(this.model.collect_view_img_elements.bind(this.model), 10);
    }

    _check_resize() {
        // Called when the widget resizes.
        // During initialization Jupyter sets .el.style.width and .height to the empty string.
        // It looks like VS Code tries harder to do this than the notebook,
        // so we need to check for this pretty aggressively.
        if (!this.el.style.width && this.model.get('css_width')) {
            this.el.style.width = this.model.get('css_width');
            this.el.style.height = this.model.get('css_height');
            // prevent massive size due to auto-scroll (issue #62)
            this.el.style.maxWidth = Math.max(1024, window.innerWidth) + 'px';
            this.el.style.maxHeight = Math.max(1024, window.innerHeight) + 'px';
            this.el.style.overflow = 'hidden';
            return;  // Don't send a resize event now
        }
        // Width and height are in logical pixels.
        let w = this.img.clientWidth;
        let h = this.img.clientHeight;
        let r = window.devicePixelRatio;
        if (w === 0 && h === 0) { return; }
        if (this._current_size[0] !== w || this._current_size[1] !== h || this._current_size[2] !== r) {
            this._current_size = [w, h, r];
            this.send_throttled({ event_type: 'resize', width: w, height: h, pixel_ratio: r, time_stamp: get_time_stamp() }, 200);
        }
    }

    send_throttled(msg, wait) {
        // Like .send(), but throttled
        let event_type = msg.event_type || '';
        let func = this._throttlers[event_type];
        if (func === undefined) {
            func = throttled(this.send, wait || 50);
            this._throttlers[event_type] = func;
        }
        func.call(this, msg);
    }
}



var KEYMAP = {
    Ctrl: 'Control',
    Del: 'Delete',
    Esc: 'Escape',
};


function get_modifiers(e) {
    let modifiers = ['Alt', 'Shift', 'Ctrl', 'Meta'].filter((n) => e[n.toLowerCase() + 'Key']);
    return modifiers.map((m) => KEYMAP[m] || m);
}


function throttled(func, wait) {
    var context, args, result;
    var timeout = null;
    var previous = 0;
    var later = function () {
        previous = Date.now();
        timeout = null;
        result = func.apply(context, args);
        if (!timeout) context = args = null;
    };
    return function () {
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


function create_pointer_event(el, e, pointers, event_type) {
    let rect = el.getBoundingClientRect();
    let offset = [rect.left, rect.top];
    let main_x = Number(e.clientX - offset[0]);
    let main_y = Number(e.clientY - offset[1]);

    // Collect touches (we may add more fields later)
    let touches = {};
    let ntouches = 0;
    for (let pointer_id in pointers) {
        let pe = pointers[pointer_id]; // pointer event
        let x = Number(pe.clientX - offset[0]);
        let y = Number(pe.clientY - offset[1]);
        let touch = { x: x, y: y, pressure: pe.pressure };
        touches[pe.pointerId] = touch;
        ntouches += 1;
    }

    // Get button that changed, and the button state
    var button = { 0: 1, 1: 3, 2: 2, 3: 4, 4: 5, 5: 6 }[e.button] || 0;
    var buttons = [];
    for (let b of [0, 1, 2, 3, 4, 5]) { if ((1 << b) & e.buttons) { buttons.push(b + 1); } }

    return {
        event_type: event_type,
        x: main_x,
        y: main_y,
        button: button,
        buttons: buttons,
        modifiers: get_modifiers(e),
        ntouches: ntouches,
        touches: touches,
        time_stamp: get_time_stamp(),
    };
}

function get_time_stamp() {
    return Date.now() / 1000;
}
