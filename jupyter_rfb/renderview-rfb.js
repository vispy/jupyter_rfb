/* global BaseRenderView getTimestamp */

/**
 * An object that represents the model (wrapping the anywidget model object), that can have multiple views.
 */
class RendercanvasAnywidgetModel {
  constructor (anymodel) {
    this.anymodel = anymodel
    this.views = []
    this._hasVisibleViews = false

    // Variables to store frames and the last frame
    this._frames = []
    this._lastSrc = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR42mOor68HAAL+AX6E2KOJAAAAAElFTkSuQmCC'
    this._lastFrame = {
      src: this._lastSrc,
      index: 0,
      timestamp: 0
    }

    // Register callbacks
    anymodel.on('msg:custom', (msg, buffers) => {
      if (msg.type === 'framebufferdata') {
        this._frames.push({ ...msg, buffers })
        this._request_animation_frame()
      }
    })
    // For traits we allow the public and private version, this means we can use the
    // same JS code for multiple anywidget implementations (specifically rendercanvas.anywidget vs jupyter_rfb)
    for (const prefix of ['', '_']) {
      anymodel.on(`change:${prefix}css_width`, () => {
        const cssWidth = anymodel.get(`${prefix}css_width`)
        for (const view of this.views) {
          view.setCssWidth(cssWidth)
        }
      })
      anymodel.on(`change:${prefix}css_height`, () => {
        const cssHeight = anymodel.get(`${prefix}css_height`)
        for (const view of this.views) {
          view.setCssHeight(cssHeight)
        }
      })
      anymodel.on(`change:${prefix}resizable`, () => {
        const resizable = anymodel.get(`${prefix}resizable`)
        for (const view of this.views) {
          view.setResizable(resizable)
        }
      })
      anymodel.on(`change:${prefix}has_titlebar`, () => {
        const titlebar = anymodel.get(`${prefix}has_titlebar`)
        for (const view of this.views) {
          view.showTitlebar(titlebar)
        }
      })
      anymodel.on(`change:${prefix}title`, () => {
        const title = anymodel.get(`${prefix}title`)
        for (const view of this.views) {
          view.setTitle(title)
        }
      })
      anymodel.on(`change:${prefix}cursor`, () => {
        const cursor = anymodel.get(`${prefix}cursor`)
        for (const view of this.views) {
          view.setCursor(cursor)
        }
      })
    }

    // Start the animation loop
    this._img_update_pending = false
    this._request_animation_frame()
  }

  close () {
    URL.revokeObjectURL(this._lastSrc)
    this._lastSrc = null
    this._lastFrame = null
    this._frames = []
    for (const view of this.views) {
      view.close()
    }
    // This gets called when the model is closed and the comm is removed. Notify Py just in time!
    const t = getTimestamp()
    const event = {
      type: 'close',
      timestamp: t
    }
    this.onEvent(event)
  }

  addView (view) {
    this.views.push(view)
    this.updateVisibility()
    // Init attrs
    const anymodel = this.anymodel
    view.setCssWidth(anymodel.get('_css_width') ?? anymodel.get('css_width'))
    view.setCssHeight(anymodel.get('_css_height') ?? anymodel.get('css_height'))
    view.setResizable(anymodel.get('_resizable') ?? anymodel.get('resizable'))
    view.showTitlebar(anymodel.get('_has_titlebar') ?? anymodel.get('has_titlebar'))
    view.setTitle(anymodel.get('_title') ?? anymodel.get('title'))
    view.setCursor(anymodel.get('_cursor') ?? anymodel.get('cursor'))
    // Init view
    if (this._lastSrc) {
      view.viewElement.src = this._lastSrc
    }
  }

  removeView (view) {
    this.views = this.views.filter(v => v !== view)
    this.updateVisibility()
  }

  updateVisibility () {
    let visibleViewsCount = 0
    for (const view of this.views) {
      if (view.isVisible) { visibleViewsCount += 1 }
    }
    const hasVisibleViews = visibleViewsCount > 0
    this.anymodel.set('_has_visible_views', hasVisibleViews)
    this.anymodel.save_changes()
    if (hasVisibleViews) {
      this._request_animation_frame()
    }
  }

  _send_response () {
    // Let Python know what we have at the frame. This prop is a dict, making it "atomic".
    const frame = this._lastFrame
    const frameFeedback = { index: frame.index, timestamp: frame.timestamp, localtime: Date.now() / 1000 }
    this.anymodel.set('_frame_feedback', frameFeedback)
    this.anymodel.save_changes()
  }

  _request_animation_frame () {
    // Request an animation frame.
    // Before the anywidget refactor, we did this via a tiny delay, which supposedly made things more smooth,
    // but it also increases the delay for a frame to hit the screen, and limits the max fps, so let's not do that.
    if (!this._img_update_pending) {
      this._img_update_pending = true
      window.requestAnimationFrame(this._animate.bind(this))
      // window.setTimeout(window.requestAnimationFrame, 5, this._animate.bind(this)) // via a delay
    }
  }

  _animate () {
    this._img_update_pending = false
    if (this._frames.length === 0) { return };

    // Pick the oldest frame from the stack, and get its source
    const frame = this._frames.shift()
    let newSrc
    if (frame.buffers.length > 0) {
      const blob = new Blob([frame.buffers[0].buffer], { type: frame.mimetype })
      newSrc = URL.createObjectURL(blob)
    } else {
      newSrc = frame.data_b64
    }

    // Revoke last objectURL
    URL.revokeObjectURL(this._lastSrc)
    this._lastSrc = newSrc

    // Update the image sources
    for (const view of this.views) {
      view.viewElement.src = newSrc
      view.viewElement.onload = this._request_animation_frame.bind(this)
    }

    // Let the server know we processed the image (even if it's not shown yet)
    this._lastFrame = frame
    this._send_response()
  }

  onEvent (event) {
    try {
      this.anymodel.send(event)
    } catch { } // probably attempt to send when widget is closed
  }
}

/**
 * View to show the anywidget output and observe events, based on renderview.js.
 */
class AnywidgetRenderView extends BaseRenderView {
  constructor (model, containerElement) {
    // Create the wrapper element
    const wrapperElement = document.createElement('div')
    wrapperElement.classList.add('renderview-wrapper')
    wrapperElement.classList.add('is-resizable')
    // wrapperElement.classList.add('has-titlebar') -> not by default
    containerElement.appendChild(wrapperElement)

    // Create img element
    const viewElement = document.createElement('img')
    viewElement.decoding = 'sync'
    viewElement.loading = 'eager'
    viewElement.style.touchAction = 'none' // prevent default pan/zoom behavior
    viewElement.ondragstart = () => false // prevent browser's built-in image drag

    // Call super
    super(viewElement, wrapperElement)
    this.setThrottle(20) // 20ms -> max 50 move/wheel events per second

    // Connect to the model, it will initialize it with the current size and frame-data
    this.model = model
    this.model.addView(this)
  }

  close () {
    super.close()
    this.model.removeView(this)
  }

  onEvent (event) {
    if (event.type === 'resize') {
      // Note that there can be multiple views that can possibly be individually resized.
      // TODO: keep logical size in check between different views?
      if (event.width * event.height > 0) {
        this.model.onEvent(event)
      }
    } else if (event.type === 'close') {
      // we don't close when one view closes, only when the widget closes
    } else if (event.type === 'show') {
      this.isVisible = true
      this.model.updateVisibility()
    } else if (event.type === 'hide') {
      this.isVisible = false
      this.model.updateVisibility()
    } else {
      this.model.onEvent(event)
    }
  }
}

// anywidget lifecycle export
export default () => {
  let model
  return {
    initialize (ctx) {
      model = new RendercanvasAnywidgetModel(ctx.model)
      // window.model = model // debug
      return () => { model.close() }
    },
    render (ctx) {
      const view = new AnywidgetRenderView(model, ctx.el)
      return () => { view.close() }
    }
  }
}
