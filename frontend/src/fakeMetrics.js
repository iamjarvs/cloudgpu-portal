// Deterministic cosmetic drift for the permanently-seeded dummy environment
// cards — identity fields (servers/VLANs/subnets) never change, only these
// numbers, and only client-side so the backend never has to compute or
// store anything for it.
function hashSeed(str) {
  let h = 0
  for (let i = 0; i < str.length; i++) {
    h = (Math.imul(31, h) + str.charCodeAt(i)) | 0
  }
  return h
}

// Deterministic fake time-series for chart widgets (utilization history,
// spend history, etc.) — same seed always produces the same series so a
// chart doesn't jump around on every re-render/reload.
export function dummySeries(seedStr, points = 24, { min = 30, max = 90 } = {}) {
  const seed = hashSeed(seedStr)
  const arr = []
  for (let i = 0; i < points; i++) {
    const t = i * 0.4 + (seed % 1000) / 1000
    const wave = (Math.sin(t) + 1) / 2
    const wobble = Math.sin(t * 3.1 + seed) * 0.08
    arr.push(Math.round((wave + wobble) * (max - min) + min))
  }
  return arr
}

export function dummyMetrics(uuid, now = Date.now()) {
  const seed = hashSeed(uuid)
  const bucket = Math.floor(now / 4000)
  const phase = ((seed % 1000) / 1000) * Math.PI * 2
  const t = bucket * 0.15 + phase

  const gpuUtilPct = Math.round(55 + 30 * Math.sin(t) + 8 * Math.sin(t * 2.7 + seed))
  const netThroughputGbps = Math.round(12 + 6 * Math.sin(t * 0.6 + seed * 0.3))
  const avgTempC = Math.round(58 + 6 * Math.sin(t * 0.4 + seed * 0.7))

  return {
    gpuUtilPct: Math.min(99, Math.max(20, gpuUtilPct)),
    netThroughputGbps: Math.max(2, netThroughputGbps),
    avgTempC: Math.min(78, Math.max(48, avgTempC)),
  }
}
