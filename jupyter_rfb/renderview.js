/*************************************************************************************************
  renderview.js

  This file is dedicated to the public domain under CC0 1.0.
  This file is developed at https://github.com/pygfx/renderview, please contribute changes there.

  This module implements a common event spec for render targets in a browser.
  The code is written with little assumptions about the application, so that it
  can be shared between different use-cases, such as rendercanvas backends
  (pyodide, anywidget, remote-browser), jupyter_rfb, and other projects.

  Code that loads this script should avoid loading it in the global scope.
  Either by putting it in a ``<script type='module>``, or wrapping it in an IIFE
  with ``(() => {\n{JS}\n})();``

  This code is formatted and linted with standardjs (quite similar to Ruff in
  Python). It adheres to common JS practices, but also has some Python habits,
  like underscore prefix for private attributes.

 *************************************************************************************************/

'use strict'

const Element = window.Element
const IntersectionObserver = window.IntersectionObserver
const ResizeObserver = window.ResizeObserver

const LOOKS_LIKE_MOBILE = /mobi|android|iphone|ipad|ipod|tablet/.test(
  navigator.userAgent.toLowerCase()
)

const KEY_MAP = {
  Ctrl: 'Control',
  Del: 'Delete',
  Esc: 'Escape'
}

const KEY_MOD_MAP = {
  altKey: 'Alt',
  ctrlKey: 'Control',
  metaKey: 'Meta',
  shiftKey: 'Shift'
}

const MOUSE_BUTTON_MAP = {
  0: 1, // left
  1: 3, // middle/wheel
  2: 2, // right
  3: 4, // backwards
  4: 5 // forwards
}

function getButtons (ev) {
  // Note that ev.button has a historic awkward mapping, but ev.buttons is in the order that we want
  const button = MOUSE_BUTTON_MAP[ev.button] || 0
  const buttons = []
  for (const b of [0, 1, 2, 3, 4, 5]) {
    if ((1 << b) & ev.buttons) {
      buttons.push(b + 1)
    }
  }
  return [button, buttons]
}

function getModifiers (ev) {
  return Object.entries(KEY_MOD_MAP)
    .filter(([k]) => ev[k])
    .map(([, v]) => v)
}

function getTimestamp () {
  return performance.now() / 1000
}

function arraysEqual (a, b) {
  return a.length === b.length && a.every((val, i) => val === b[i])
}

/**
 * The BaseRenderView handles the client-side logic for a render target (typically a <canvas> or <img>).
 *
 * It observes events and calls `this.OnEvent()`.
 * It provides convenience methods for setting the size, cursor, and more.
 *
 * When used with a wrapper element, more features are enabled:
 *
 * - It can be manually resized if the wrapper element has the 'is-resizable' class.
 * - A title bar is shown if the wrapper has the 'has-titlebar' class.
 * - The above mentioned classes can also be programmatically set via `setResizable()` and `showTitlebar()`.
 * - The title can be set using `setTitle()`.
 *
 */
class BaseRenderView {
  /**
   * Create a new RenderView.
   *
   * If a single element is given, the view directly manages that element, nice and simple.
   * No styling is applied except for `width` and `height`.
   *
   * If a wrapper element is also given, the view supports features like manual resizing and a title-bar.
   * In this case, any user styling that effects positioning should be applied to the wrapper.
   * The wrapper may contain placeholder content; on initialization, it's innerHTML and padding are reset.
   *
   * @param {HTMLElement} viewElement - The element (e.g. canvas or img) used for rendering.
   * @param {HTMLElement} wrapperElement - The wrapper element (optional; can be null).
   */
  constructor (viewElement, wrapperElement) {
    // Check given element
    if (viewElement === undefined || !(viewElement instanceof Element)) {
      throw new Error('BaseRenderView: viewElement must be an Element.')
    }
    if (wrapperElement !== null) {
      if (wrapperElement === undefined || !(wrapperElement instanceof Element)) {
        throw new Error('BaseRenderView: wrapperElement must be null or an Element.')
      }
      wrapperElement.innerHTML = ''
      wrapperElement.style.padding = '0'
      wrapperElement.style.background = ''
    }

    // Tweak viewElement
    viewElement.tabIndex = -1
    // Prevent context menu on RMB. Firefox still shows it when shift is pressed. It seems
    // impossible to override this (tips welcome!), so let's make this the actual behavior.
    viewElement.oncontextmenu = (e) => {
      if (!e.shiftKey) {
        e.preventDefault()
        e.stopPropagation()
        return false
      }
    }

    this.viewElement = viewElement
    this.wrapperElement = wrapperElement
    this.sizeElement = (wrapperElement === null) ? viewElement : wrapperElement
    this.titleElement = null // is set in _initElements() if wrapperElement is given

    this._lsize = null // cached logical size
    this._wheelThrottle = 20 // to avoid flooding wheel events
    this._moveThrottle = 20 // to avoid flooding move events
    this._isVisible = false // set by intersection observer

    this._focusElement = null
    this._abortController = new AbortController()
    this._resizeObserver = null
    this._intersectionObserver = null

    this._initElements()
    this._registerEvents()
  }

  /**
   * Close the view, disconnecting observers and clearing callbacks.
   * This does not remove the the element from the DOM; that's up to the caller.
   */
  close () {
    if (this._focusElement) {
      this._focusElement.remove()
      this._focusElement = null
    }
    if (this._abortController) {
      this._abortController.abort()
      this._abortController = null
    }
    if (this._resizeObserver) {
      this._resizeObserver.disconnect()
      this._resizeObserver = null
    }
    if (this._intersectionObserver) {
      this._intersectionObserver.disconnect()
      this._intersectionObserver = null
    }
    this.viewElement = null
    this.sizeElement = null
    this.titleElement = null
    if (this.wrapperElement) {
      this.wrapperElement.innerHTML = ''
      this.wrapperElement = null
    }
    const event = {
      type: 'close',
      timestamp: getTimestamp()
    }
    this.onEvent(event)
  }

  /**
   * Set the view's size in logical pixels.
   *
   * @param {string} width - The requested width.
   * @param {string} height - The requested height.
   */
  setLogicalSize (width, height) {
    this.sizeElement.style.maxWidth = ''
    this.sizeElement.style.maxHeight = ''
    this.sizeElement.style.width = width + 'px'
    this.sizeElement.style.height = height + 'px'
  }

  /**
   * Set the width of the view as a CSS string.
   *
   * @param {string} cssWidth - The requested width as a css string, e.g. '640px' or '90%' or 'calc(100% - 10px)'.
   */
  setCssWidth (cssWidth) {
    this.sizeElement.style.maxWidth = ''
    this.sizeElement.style.width = cssWidth
  }

  /**
   * Set the height of the view as a CSS string.
   *
   * @param {string} cssHeight - The requested height as a css string, e.g. '480px' or '40vh'.
   */
  setCssHeight (cssHeight) {
    this.sizeElement.style.maxHeight = ''
    this.sizeElement.style.height = cssHeight
  }

  /**
   * Set whether the view is manually resizable.
   * Note that the view can only be made resizable if it was instantiated with a wrapper.
   *
   * @param {boolean} resizable - Whether to make it resizable or not.
   */
  setResizable (resizable) {
    if (this.wrapperElement) {
      if (resizable) {
        this.wrapperElement.classList.add('is-resizable')
      } else {
        this.wrapperElement.classList.remove('is-resizable')
      }
    }
  }

  /**
   * Set whether the view has a titlebar.
   * Note that the view can only have a titlebar if it was instantiated with a wrapper.
   *
   * @param {boolean} titlebar - Whether to show the titlebar or not.
   */
  showTitlebar (titlebar) {
    if (this.wrapperElement) {
      if (titlebar) {
        this.wrapperElement.classList.add('has-titlebar')
      } else {
        this.wrapperElement.classList.remove('has-titlebar')
      }
    }
  }

  /**
   * Set the view's title in the titlebar.
   *
   * Note that the title is only visible if the view was instantiated with a wrapper,
   * and the titlebar is shown.
   *
   * @param {string} title - The title to set.
   */
  setTitle (title) {
    if (this.titleElement) {
      this.titleElement.innerText = title
    }
  }

  /**
   * Set the `style.cursor`.
   *
   * @param {string} cursor - A valid string for CSS cursor.
   */
  setCursor (cursor) {
    this.viewElement.style.cursor = cursor
  }

  /**
   * Set the throttle setting. Set to zero to disable throttling.
   *
   * @param {number} throttle - The timeout (in ms) to wait before sending a move/wheel event.
   */
  setThrottle (throttle) {
    this._wheelThrottle = throttle
    this._moveThrottle = throttle
  }

  /**
   * The subclass should implement this to handle events.
   *
   * @param {object} event - The event object as a 'dictionary', following the spec.
   */
  onEvent (event) { }

  /**
   * Internal method to initialize the view's helper elements.
   */
  _initElements () {
    const signal = this._abortController.signal

    // Obtain container to put our hidden focus element.
    // Putting the focusElement as a child of the canvas prevents chrome from emitting input events.
    const focusElementContainerId = 'rendercanvas-focus-element-container'
    let focusElementContainer = document.getElementById(focusElementContainerId)

    if (!focusElementContainer) {
      focusElementContainer = document.createElement('div')
      focusElementContainer.setAttribute('id', focusElementContainerId)
      focusElementContainer.style.position = 'absolute'
      focusElementContainer.style.top = '0'
      focusElementContainer.style.left = '-9999px'
      document.body.appendChild(focusElementContainer)
    }

    // Create an element to which we transfer focus, so we can capture key events and prevent global shortcuts
    const focusElement = document.createElement('input')
    this._focusElement = focusElement
    focusElement.type = 'text'
    focusElement.tabIndex = -1
    focusElement.autocomplete = 'off'
    focusElement.autocorrect = 'off'
    focusElement.autocapitalize = 'off'
    focusElement.spellcheck = false
    focusElement.style.width = '1px'
    focusElement.style.height = '1px'
    focusElement.style.padding = '0'
    focusElement.style.opacity = 0
    focusElement.style.pointerEvents = 'none'
    focusElementContainer.appendChild(focusElement)

    const wrapperElement = this.wrapperElement

    if (wrapperElement !== null) {
      this.viewElement.classList.add('renderview-view')

      // Wrap it
      wrapperElement.classList.add('renderview-wrapper')
      wrapperElement.appendChild(this.viewElement)

      // Debug element
      const debugElement = document.createElement('div')
      debugElement.innerHTML = '<b>If you can read this, the rendercanvas.css is likely not applied.</b>'
      debugElement.classList.add('renderview-hidden')
      wrapperElement.appendChild(debugElement)

      // Create title bar
      const topElement = document.createElement('div')
      topElement.classList.add('renderview-top')
      const titleElement = document.createElement('span')
      this.titleElement = titleElement
      titleElement.innerText = 'RenderView'
      topElement.appendChild(titleElement)
      wrapperElement.appendChild(topElement)

      // Enable resizing
      const resizeElement = document.createElement('div')
      resizeElement.classList.add('renderview-resizer')
      wrapperElement.appendChild(resizeElement)
      let resizeInfo = null
      resizeElement.addEventListener('pointerdown', (ev) => {
        if (this._lsize) {
          resizeInfo = { w: this._lsize[0], h: this._lsize[1], x: ev.clientX, y: ev.clientY }
          resizeElement.setPointerCapture(ev.pointerId)
        }
      },
      { signal }
      )
      resizeElement.addEventListener('pointermove', (ev) => {
        if (resizeInfo !== null) {
          this.sizeElement.style.maxWidth = ''
          this.sizeElement.style.maxHeight = ''
          this.sizeElement.style.width = resizeInfo.w + (ev.clientX - resizeInfo.x) + 'px'
          this.sizeElement.style.height = resizeInfo.h + (ev.clientY - resizeInfo.y) + 'px'
        }
      },
      { signal }
      )
      resizeElement.addEventListener('lostpointercapture', (ev) => {
        resizeInfo = null
      },
      { signal }
      )
    } // wrapperElement !== null
  }

  /**
   * Internal method to setup listeners and register callbacks.
   */
  _registerEvents () {
    // Register events

    const viewElement = this.viewElement
    const signal = this._abortController.signal // to unregister/abort stuff

    // ----- visibility ---------------

    this._intersectionObserver = new IntersectionObserver((entries, observer) => {
      // This gets called when one of the observed elements becomes visible/invisible.
      // Note that entries only contains the *changed* elements, so we keep track ourselves.
      let isVisible = false
      for (const entry of entries) {
        isVisible = isVisible || entry.isIntersecting
      }
      if (isVisible !== this._isVisible) {
        this._isVisible = isVisible
        const event = {
          type: isVisible ? 'show' : 'hide',
          timestamp: getTimestamp()
        }
        this.onEvent(event)
      }
    })
    this._intersectionObserver.observe(viewElement)

    // ----- resize ---------------

    this._resizeObserver = new ResizeObserver((entries) => {
      // The physical size is easy. The logical size can be much more tricky
      // to obtain due to all the CSS stuff. But the base class will just calculate that
      // from the physical size and the pixel ratio.

      // Select entry matching our element
      const ourEntries = entries.filter((entry) => entry.target.id === viewElement.id)
      if (!ourEntries.length) {
        return
      }

      const entry = ourEntries[0]
      const ratio = window.devicePixelRatio
      let physicalWidth
      let physicalHeight

      if (entry.devicePixelContentBoxSize) {
        physicalWidth = entry.devicePixelContentBoxSize[0].inlineSize
        physicalHeight = entry.devicePixelContentBoxSize[0].blockSize
      } else {
        // Some browsers don't support devicePixelContentBoxSize
        let lsize
        if (entry.contentBoxSize) {
          lsize = [
            entry.contentBoxSize[0].inlineSize,
            entry.contentBoxSize[0].blockSize
          ]
        } else {
          lsize = [entry.contentRect.width, entry.contentRect.height]
        }
        physicalWidth = Math.floor(lsize[0] * ratio)
        physicalHeight = Math.floor(lsize[1] * ratio)
      }

      // If the container element does not have its size set via its style, we set it to the logical size.
      const logicalWidth = physicalWidth / ratio
      const logicalHeight = physicalHeight / ratio

      // prevent massive size due to auto-scroll (https://github.com/vispy/jupyter_rfb/issues/62)
      if (!this.sizeElement.style.width) {
        this.sizeElement.style.width = `${logicalWidth}px`
        this.sizeElement.style.maxWidth = '90vmin'
      }
      if (!this.sizeElement.style.height) {
        this.sizeElement.style.height = `${logicalHeight}px`
        this.sizeElement.style.maxHeight = '90vmin'
      }

      // Store logical size
      this._lsize = [logicalWidth, logicalHeight]

      const event = {
        type: 'resize',
        width: logicalWidth,
        height: logicalHeight,
        pwidth: physicalWidth,
        pheight: physicalHeight,
        ratio,
        timestamp: getTimestamp()
      }
      this.onEvent(event)
    })

    this._resizeObserver.observe(this.viewElement)

    // ----- pointer ---------------

    // Current pointer ids, mapping to initial button
    const pointerToButton = {}

    // The last used buttons, so we can pass to wheel event
    let lastButtons = []

    viewElement.addEventListener('pointerdown', (ev) => {
      // When pointer is down, set focus to the focus-element.
      if (!LOOKS_LIKE_MOBILE) {
        this._focusElement.focus({ preventScroll: true, focusVisble: false })
      }
      // capture the pointing device.
      // Because we capture the event, there will be no other events when buttons are pressed down,
      // although they will end up in the 'buttons'. The lost/release will only get fired when all buttons
      // are released/lost. Which is why we look up the original button in our `pointers` list.
      viewElement.setPointerCapture(ev.pointerId)
      // Prevent default unless alt is pressed
      if (!ev.altKey) {
        ev.preventDefault()
      }

      // Collect info
      const [button, buttons] = getButtons(ev)
      const modifiers = getModifiers(ev)

      // Manage
      pointerToButton[ev.pointerId] = button
      lastButtons = buttons

      const event = {
        type: 'pointer_down',
        x: ev.offsetX,
        y: ev.offsetY,
        button,
        buttons,
        modifiers,
        ntouches: 0, // TODO later: maybe via https://developer.mozilla.org/en-US/docs/Web/API/TouchEvent
        touches: {},
        timestamp: getTimestamp()
      }
      this.onEvent(event)
    },
    { signal }
    )

    let pendingMoveEvent = null

    const sendMoveEvent = () => {
      if (pendingMoveEvent !== null) {
        const event = pendingMoveEvent
        pendingMoveEvent = null
        this.onEvent(event)
      }
    }

    viewElement.addEventListener('pointermove', (ev) => {
      // If this pointer is not down, but other pointers are, don't emit an event.
      if (pointerToButton[ev.pointerId] === undefined) {
        if (Object.keys(pointerToButton).length > 0) {
          return
        }
      }

      // Collect info, use button that started this drag-action
      let [button, buttons] = getButtons(ev)
      const modifiers = getModifiers(ev)
      button = pointerToButton[ev.pointerId] || 0

      // Manage
      lastButtons = buttons

      // This event is throttled. We either update the pending event or create a new one
      if (
        pendingMoveEvent !== null &&
        arraysEqual(pendingMoveEvent.buttons, buttons) &&
        arraysEqual(pendingMoveEvent.modifiers, modifiers)
      ) {
        pendingMoveEvent.x = ev.offsetX
        pendingMoveEvent.y = ev.offsetY
      } else {
        const event = {
          type: 'pointer_move',
          x: ev.offsetX,
          y: ev.offsetY,
          button,
          buttons,
          modifiers,
          ntouches: 0,
          touches: {},
          timestamp: getTimestamp()
        }
        if (this._moveThrottle > 0) {
          sendMoveEvent() // Send previous (if any)
          pendingMoveEvent = event
          window.setTimeout(sendMoveEvent, this._moveThrottle)
        } else {
          this.onEvent(event)
        }
      }
    },
    { signal }
    )

    viewElement.addEventListener('lostpointercapture', (ev) => {
      // This happens on pointer-up or pointer-cancel. We threat them the same.

      // Get info, use the button stat started the drag-action
      const modifiers = getModifiers(ev)
      const button = pointerToButton[ev.pointerId] || 0
      const buttons = []

      // Manage
      delete pointerToButton[ev.pointerId]
      lastButtons = buttons

      const event = {
        type: 'pointer_up',
        x: ev.offsetX,
        y: ev.offsetY,
        button,
        buttons,
        modifiers,
        ntouches: 0,
        touches: {},
        timestamp: getTimestamp()
      }
      this.onEvent(event)
    },
    { signal }
    )

    viewElement.addEventListener('pointerenter', (ev) => {
      // If this pointer is not down, but other pointers are, don't emit an event.
      if (pointerToButton[ev.pointerId] === undefined) {
        if (Object.keys(pointerToButton).length > 0) {
          return
        }
      }

      // Collect info, but use button 0. It usually is, and should be.
      let [button, buttons] = getButtons(ev)
      const modifiers = getModifiers(ev)
      button = 0

      const event = {
        type: 'pointer_enter',
        x: ev.offsetX,
        y: ev.offsetY,
        button,
        buttons,
        modifiers,
        ntouches: 0,
        touches: {},
        timestamp: getTimestamp()
      }
      this.onEvent(event)
    },
    { signal }
    )

    viewElement.addEventListener('pointerleave', (ev) => {
      // If this pointer is not down, but other pointers are, don't emit an event.
      if (pointerToButton[ev.pointerId] === undefined) {
        if (Object.keys(pointerToButton).length > 0) {
          return
        }
      }

      // Collect info, but use button 0. It usually is, and should be.
      let [button, buttons] = getButtons(ev)
      const modifiers = getModifiers(ev)
      button = 0

      const event = {
        type: 'pointer_leave',
        x: ev.offsetX,
        y: ev.offsetY,
        button,
        buttons,
        modifiers,
        ntouches: 0,
        touches: {},
        timestamp: getTimestamp()
      }
      this.onEvent(event)
    },
    { signal }
    )

    // ----- click ---------------

    // Click events are not pointer events. In most apps that this targets, click events
    // don't add much over pointer events. But double-click can be useful.
    viewElement.addEventListener('dblclick', (ev) => {
      // Prevent default unless alt is pressed
      if (!ev.altKey) {
        ev.preventDefault()
      }

      // Collect info
      const [button, buttons] = getButtons(ev)
      const modifiers = getModifiers(ev)

      const event = {
        type: 'double_click',
        x: ev.offsetX,
        y: ev.offsetY,
        button,
        buttons,
        modifiers,
        // no touches here
        timestamp: getTimestamp()
      }
      this.onEvent(event)
    },
    { signal }
    )

    // ----- wheel ---------------

    let pendingWheelEvent = null

    const sendWheelEvent = () => {
      if (pendingWheelEvent !== null) {
        const event = pendingWheelEvent
        pendingWheelEvent = null
        this.onEvent(event)
      }
    }

    viewElement.addEventListener('wheel', (ev) => {
      // Only scroll if we have focus
      if (window.document.activeElement !== this._focusElement) {
        return
      }
      // Prevent default unless alt is pressed
      if (!ev.altKey) {
        ev.preventDefault()
      }

      // Collect info
      const scales = [1 / window.devicePixelRatio, 16, 600] // pixel, line, page
      const scale = scales[ev.deltaMode]
      const modifiers = getModifiers(ev)
      const buttons = [...lastButtons]

      // This event is throttled. We either update the pending event or create a new one
      if (
        pendingWheelEvent !== null &&
        arraysEqual(pendingWheelEvent.buttons, buttons) &&
        arraysEqual(pendingWheelEvent.modifiers, modifiers)
      ) {
        pendingWheelEvent.x = ev.offsetX
        pendingWheelEvent.y = ev.offsetY
        pendingWheelEvent.dx += ev.deltaX * scale
        pendingWheelEvent.dy += ev.deltaY * scale
      } else {
        const event = {
          type: 'wheel',
          x: ev.offsetX,
          y: ev.offsetY,
          dx: ev.deltaX * scale,
          dy: ev.deltaY * scale,
          buttons,
          modifiers,
          timestamp: getTimestamp()
        }
        if (this._wheelThrottle > 0) {
          sendWheelEvent() // Send previous (if any)
          pendingWheelEvent = event
          window.setTimeout(sendWheelEvent, this._wheelThrottle)
        } else {
          this.onEvent(event)
        }
      }
    },
    { signal }
    )

    // ----- key ---------------

    this._focusElement.addEventListener('keydown', (ev) => {
      // Failsafe in case the element is deleted or detached.
      if (this.sizeElement.offsetParent === null) {
        return
      }
      // Ignore repeated events (key being held down)
      if (ev.repeat) {
        return
      }
      // No need for stopPropagation or preventDefault because we are in a text-input.

      const modifiers = getModifiers(ev)

      const event = {
        type: 'key_down',
        key: KEY_MAP[ev.key] || ev.key,
        modifiers,
        timestamp: getTimestamp()
      }
      this.onEvent(event)
    },
    { signal }
    )

    this._focusElement.addEventListener('keyup', (ev) => {
      if (this.sizeElement.offsetParent === null) {
        return
      }

      const modifiers = getModifiers(ev)

      const event = {
        type: 'key_up',
        key: KEY_MAP[ev.key] || ev.key,
        modifiers,
        timestamp: getTimestamp()
      }
      this.onEvent(event)
    },
    { signal }
    )

    this._focusElement.addEventListener('input', (ev) => {
      // Failsafe in case the element is deleted or detached.
      if (this.sizeElement.offsetParent === null) {
        return
      }
      // Prevent the text box from growing
      if (!ev.isComposing) {
        this.focus_el.value = ''
      }

      const event = {
        type: 'char',
        data: ev.data,
        is_composing: ev.isComposing,
        input_type: ev.inputType,
        // repeat: ev.repeat,  // n.a.
        timestamp: getTimestamp()
      }
      this.onEvent(event)
    },
    { signal }
    )
  }
}

// Export
window.BaseRenderView = BaseRenderView
