import * as faceapi from '@vladmandic/face-api'

let modelsLoaded = false
let loadingPromise = null

// Models are served from public/models (copied there automatically by
// scripts/copy-face-models.mjs on `npm install`), so this works without
// any live internet connection during a demo.
const MODEL_URL = '/models'

export function loadFaceModels() {
    if (modelsLoaded) return Promise.resolve()
    if (loadingPromise) return loadingPromise

    loadingPromise = Promise.all([
        faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
        faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL),
        faceapi.nets.faceRecognitionNet.loadFromUri(MODEL_URL),
    ]).then(() => { modelsLoaded = true })

    return loadingPromise
}

/**
 * Runs real face detection + landmark extraction + descriptor computation
 * on the given <video> element. Returns a 128-number array (the face's
 * numeric "fingerprint") or null if no face was confidently detected.
 * This is a single-frame capture -- matching against the enrolled
 * descriptor (done server-side) is what actually verifies identity.
 */
export async function captureFaceDescriptor(videoEl) {
    const detection = await faceapi
        .detectSingleFace(videoEl, new faceapi.TinyFaceDetectorOptions())
        .withFaceLandmarks()
        .withFaceDescriptor()

    if (!detection) return null
    return Array.from(detection.descriptor)
}
export async function captureAveragedDescriptor(videoEl, samples = 5, intervalMs = 300) {
    const descs = []
    for (let i = 0; i < samples; i++) {
        const d = await captureFaceDescriptor(videoEl)
        if (!d) return null // face lost mid-capture
        descs.push(d)
        await new Promise(r => setTimeout(r, intervalMs))
    }
    const mean = new Array(128).fill(0)
    descs.forEach(d => d.forEach((v, i) => { mean[i] += v / descs.length }))
    const dist = (a, b) => Math.sqrt(a.reduce((s, v, i) => s + (v - b[i]) ** 2, 0))
    if (descs.some(d => dist(d, mean) > 0.3)) return null // frames disagree
    return mean
}