import { useEffect, useRef } from 'react'

// ─── Default shader (purple nebula / space) ───────────────────────────────────
const SHADER_SRC = `#version 300 es
/*
 * Adapted from Matthias Hurrle (@atzedent)
 * "To boldly go where no man has gone before."
 */
precision highp float;
out vec4 O;
uniform vec2 resolution;
uniform float time;
#define FC gl_FragCoord.xy
#define T time
#define R resolution
#define MN min(R.x,R.y)

float rnd(vec2 p) {
  p = fract(p * vec2(12.9898, 78.233));
  p += dot(p, p + 34.56);
  return fract(p.x * p.y);
}
float noise(in vec2 p) {
  vec2 i = floor(p), f = fract(p), u = f * f * (3. - 2. * f);
  float a = rnd(i), b = rnd(i + vec2(1,0)), c = rnd(i + vec2(0,1)), d = rnd(i + 1.);
  return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}
float fbm(vec2 p) {
  float t = .0, a = 1.; mat2 m = mat2(1., -.5, .2, 1.2);
  for (int i = 0; i < 5; i++) { t += a * noise(p); p *= 2. * m; a *= .5; }
  return t;
}
float clouds(vec2 p) {
  float d = 1., t = .0;
  for (float i = .0; i < 3.; i++) {
    float a = d * fbm(i * 10. + p.x * .2 + .2 * (1. + i) * p.y + d + i * i + p);
    t = mix(t, d, a); d = a; p *= 2. / (i + 1.);
  }
  return t;
}
void main(void) {
  vec2 uv = (FC - .5 * R) / MN, st = uv * vec2(2, 1);
  vec3 col = vec3(0);
  float bg = clouds(vec2(st.x + T * .5, -st.y));
  uv *= 1. - .3 * (sin(T * .2) * .5 + .5);
  for (float i = 1.; i < 12.; i++) {
    uv += .1 * cos(i * vec2(.1 + .01 * i, .8) + i * i + T * .5 + .1 * uv.x);
    vec2 p = uv;
    float d = length(p);
    col += .00125 / d * (cos(sin(i) * vec3(2.5, 1.0, 3.5)) + 1.);
    float b = noise(i + p + bg * 1.731);
    col += .002 * b / length(max(p, vec2(b * p.x * .02, p.y)));
    col = mix(col, vec3(bg * .20, bg * .03, bg * .25), d);
  }
  O = vec4(col, 1);
}`

// ─── WebGL renderer ──────────────────────────────────────────────────────────
class WebGLRenderer {
  constructor(canvas, scale) {
    this.canvas = canvas
    this.scale = scale
    this.gl = canvas.getContext('webgl2')
    this.program = null
    this.vs = null
    this.fs = null
    this.buffer = null
    this.mouseMove = [0, 0]
    this.mouseCoords = [0, 0]
    this.pointerCoords = [0, 0]
    this.nbrOfPointers = 0

    this.vertexSrc = `#version 300 es
precision highp float;
in vec4 position;
void main(){ gl_Position = position; }`

    this.vertices = [-1, 1, -1, -1, 1, 1, 1, -1]
    if (this.gl) {
      this.gl.viewport(0, 0, canvas.width * scale, canvas.height * scale)
    }
  }

  compile(shader, source) {
    const { gl } = this
    gl.shaderSource(shader, source)
    gl.compileShader(shader)
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      console.error('Shader compile error:', gl.getShaderInfoLog(shader))
    }
  }

  test(source) {
    const { gl } = this
    const shader = gl.createShader(gl.FRAGMENT_SHADER)
    gl.shaderSource(shader, source)
    gl.compileShader(shader)
    const ok = gl.getShaderParameter(shader, gl.COMPILE_STATUS)
    const err = ok ? null : gl.getShaderInfoLog(shader)
    gl.deleteShader(shader)
    return err
  }

  reset() {
    const { gl } = this
    if (this.program && !gl.getProgramParameter(this.program, gl.DELETE_STATUS)) {
      if (this.vs) { gl.detachShader(this.program, this.vs); gl.deleteShader(this.vs) }
      if (this.fs) { gl.detachShader(this.program, this.fs); gl.deleteShader(this.fs) }
      gl.deleteProgram(this.program)
    }
  }

  setup() {
    const { gl } = this
    this.vs = gl.createShader(gl.VERTEX_SHADER)
    this.fs = gl.createShader(gl.FRAGMENT_SHADER)
    this.compile(this.vs, this.vertexSrc)
    this.compile(this.fs, SHADER_SRC)
    this.program = gl.createProgram()
    gl.attachShader(this.program, this.vs)
    gl.attachShader(this.program, this.fs)
    gl.linkProgram(this.program)
    if (!gl.getProgramParameter(this.program, gl.LINK_STATUS)) {
      console.error(gl.getProgramInfoLog(this.program))
    }
  }

  init() {
    const { gl } = this
    const p = this.program
    this.buffer = gl.createBuffer()
    gl.bindBuffer(gl.ARRAY_BUFFER, this.buffer)
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(this.vertices), gl.STATIC_DRAW)

    const pos = gl.getAttribLocation(p, 'position')
    gl.enableVertexAttribArray(pos)
    gl.vertexAttribPointer(pos, 2, gl.FLOAT, false, 0, 0)

    p._res = gl.getUniformLocation(p, 'resolution')
    p._time = gl.getUniformLocation(p, 'time')
    p._move = gl.getUniformLocation(p, 'move')
    p._touch = gl.getUniformLocation(p, 'touch')
    p._ptrs = gl.getUniformLocation(p, 'pointers')
    p._npts = gl.getUniformLocation(p, 'pointerCount')
  }

  updateScale(scale) {
    this.scale = scale
    this.gl.viewport(0, 0, this.canvas.width * scale, this.canvas.height * scale)
  }
  updateMove(d) { this.mouseMove = d }
  updateMouse(c) { this.mouseCoords = c }
  updatePointerCoords(c) { this.pointerCoords = c }
  updatePointerCount(n) { this.nbrOfPointers = n }

  render(now = 0) {
    const { gl } = this
    const p = this.program
    if (!p || gl.getProgramParameter(p, gl.DELETE_STATUS)) return
    gl.clearColor(0, 0, 0, 1)
    gl.clear(gl.COLOR_BUFFER_BIT)
    gl.useProgram(p)
    gl.bindBuffer(gl.ARRAY_BUFFER, this.buffer)
    gl.uniform2f(p._res, this.canvas.width, this.canvas.height)
    gl.uniform1f(p._time, now * 1e-3)
    gl.uniform2f(p._move, ...this.mouseMove)
    gl.uniform2f(p._touch, ...this.mouseCoords)
    gl.uniform1i(p._npts, this.nbrOfPointers)
    gl.uniform2fv(p._ptrs, this.pointerCoords)
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4)
  }
}

// ─── Pointer handler ─────────────────────────────────────────────────────────
class PointerHandler {
  constructor(element, scale) {
    this.scale = scale
    this.active = false
    this.pointers = new Map()
    this.lastCoords = [0, 0]
    this.moves = [0, 0]

    const map = (el, s, x, y) => [x * s, el.height - y * s]

    element.addEventListener('pointerdown', (e) => {
      this.active = true
      this.pointers.set(e.pointerId, map(element, this.scale, e.clientX, e.clientY))
    })
    element.addEventListener('pointerup', (e) => {
      if (this.count === 1) this.lastCoords = this.first
      this.pointers.delete(e.pointerId)
      this.active = this.pointers.size > 0
    })
    element.addEventListener('pointerleave', (e) => {
      if (this.count === 1) this.lastCoords = this.first
      this.pointers.delete(e.pointerId)
      this.active = this.pointers.size > 0
    })
    element.addEventListener('pointermove', (e) => {
      if (!this.active) return
      this.lastCoords = [e.clientX, e.clientY]
      this.pointers.set(e.pointerId, map(element, this.scale, e.clientX, e.clientY))
      this.moves = [this.moves[0] + e.movementX, this.moves[1] + e.movementY]
    })
  }

  get count() { return this.pointers.size }
  get move() { return this.moves }
  get coords() {
    return this.pointers.size > 0 ? Array.from(this.pointers.values()).flat() : [0, 0]
  }
  get first() {
    const v = this.pointers.values().next().value
    return v || this.lastCoords
  }
}

// ─── Hook ─────────────────────────────────────────────────────────────────────
function useShaderBackground() {
  const canvasRef = useRef(null)
  const rafRef = useRef(null)
  const rendererRef = useRef(null)
  const pointersRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const dpr = Math.max(1, 0.5 * window.devicePixelRatio)

    const resize = () => {
      if (!canvas) return
      canvas.width = window.innerWidth * dpr
      canvas.height = window.innerHeight * dpr
      rendererRef.current?.updateScale(dpr)
    }

    const loop = (now) => {
      const r = rendererRef.current
      const p = pointersRef.current
      if (!r || !p) return
      r.updateMouse(p.first)
      r.updatePointerCount(p.count)
      r.updatePointerCoords(p.coords)
      r.updateMove(p.move)
      r.render(now)
      rafRef.current = requestAnimationFrame(loop)
    }

    const gl = canvas.getContext('webgl2')
    if (!gl) {
      // WebGL2 not available — silently skip, fallback bg remains
      return
    }

    rendererRef.current = new WebGLRenderer(canvas, dpr)
    pointersRef.current = new PointerHandler(canvas, dpr)

    rendererRef.current.setup()
    rendererRef.current.init()

    resize()
    rafRef.current = requestAnimationFrame(loop)
    window.addEventListener('resize', resize)

    return () => {
      window.removeEventListener('resize', resize)
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      rendererRef.current?.reset()
    }
  }, [])

  return canvasRef
}

// ─── Exported canvas component ───────────────────────────────────────────────
export function ShaderCanvas({ className = '' }) {
  const canvasRef = useShaderBackground()
  return (
    <canvas
      ref={canvasRef}
      className={`shader-canvas ${className}`}
      style={{ background: '#000' }}
    />
  )
}

export default ShaderCanvas