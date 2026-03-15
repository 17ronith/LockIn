import CelestialBloomShader from './celestial-bloom-shader.jsx'

export default function DemoOne() {
  return (
    <div className="app-container">
      <CelestialBloomShader />
      <div className="content-overlay">
        <h1>Celestial Bloom</h1>
        <p>A Procedural Shader Animation</p>
      </div>
    </div>
  )
}