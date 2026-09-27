// A lightweight, stable per-browser device fingerprint for the demo.
// In production this would be a real fingerprinting library (e.g.
// FingerprintJS); here we generate a random id once and persist it in
// localStorage so returning visits are recognised as the "same device".

const KEY = 'fg_device_fingerprint'

export function getDeviceFingerprint() {
  let fp = localStorage.getItem(KEY)
  if (!fp) {
    fp = 'fp_' + Math.random().toString(36).slice(2) + Date.now().toString(36)
    localStorage.setItem(KEY, fp)
  }
  return fp
}

export function resetDeviceFingerprint() {
  const fp = 'fp_' + Math.random().toString(36).slice(2) + Date.now().toString(36)
  localStorage.setItem(KEY, fp)
  return fp
}

export function detectBrowser() {
  const ua = navigator.userAgent
  if (ua.includes('Edg/')) return 'Edge'
  if (ua.includes('Chrome/')) return 'Chrome'
  if (ua.includes('Firefox/')) return 'Firefox'
  if (ua.includes('Safari/')) return 'Safari'
  return 'Unknown Browser'
}

export function detectOS() {
  const ua = navigator.userAgent
  if (ua.includes('Windows')) return 'Windows'
  if (ua.includes('Mac OS')) return 'macOS'
  if (ua.includes('Android')) return 'Android'
  if (ua.includes('iPhone') || ua.includes('iPad')) return 'iOS'
  if (ua.includes('Linux')) return 'Linux'
  return 'Unknown OS'
}
