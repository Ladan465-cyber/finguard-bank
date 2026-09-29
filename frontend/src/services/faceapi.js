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

// Eye Aspect Ratio: a standard, well-established liveness signal. It's the
// ratio of an eye's height to its width, computed from 6 landmark points
// around the eye. A real eye closing during a blink makes this ratio drop
// sharply for a few frames; a static photo's "eyes" never change ratio at
// all, which is exactly what lets us tell the two apart.
function eyeAspectRatio(eyePoints) {
  const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y)
  const vertical1 = dist(eyePoints[1], eyePoints[5])
  const vertical2 = dist(eyePoints[2], eyePoints[4])
  const horizontal = dist(eyePoints[0], eyePoints[3])
  return (vertical1 + vertical2) / (2 * horizontal)
}

/**
 * Runs face detection repeatedly over a short window (default 2.5s),
 * watching for a genuine blink (a dip in eye-aspect-ratio) as a liveness
 * check, and keeps the highest-confidence frame's descriptor to use for
 * matching. Returns null fields if no face / no blink was found.
 */
export async function captureWithLiveness(
  videoEl,
  { durationMs = 2500, sampleIntervalMs = 150, blinkThreshold = 0.23 } = {}
) {
    const start = Date.now()
  let minEAR = Infinity
  let framesWithFace = 0
  let bestDetection = null
  let bestScore = -1
  let sampleCount = 0

  console.log('[FinShield DEBUG] video element size:', videoEl.videoWidth, 'x', videoEl.videoHeight, 'readyState:', videoEl.readyState)

  while (Date.now() - start < durationMs) {
    sampleCount += 1
    let detection = null
    try {
      detection = await faceapi
        .detectSingleFace(videoEl, new faceapi.TinyFaceDetectorOptions())
        .withFaceLandmarks()
        .withFaceDescriptor()
    } catch (err) {
      console.log('[FinShield DEBUG] detection threw an error on sample', sampleCount, ':', err)
    }

    console.log('[FinShield DEBUG] sample', sampleCount, '-> detection found:', !!detection, detection ? `score=${detection.detection.score.toFixed(3)}` : '')

    if (detection) {
      framesWithFace += 1
      const leftEAR = eyeAspectRatio(detection.landmarks.getLeftEye())
      const rightEAR = eyeAspectRatio(detection.landmarks.getRightEye())
      const avgEAR = (leftEAR + rightEAR) / 2
      if (avgEAR < minEAR) minEAR = avgEAR

      if (detection.detection.score > bestScore) {
        bestScore = detection.detection.score
        bestDetection = detection
      }
    }
    await new Promise((resolve) => setTimeout(resolve, sampleIntervalMs))
  }

  const blinkDetected = minEAR < blinkThreshold

  if (!bestDetection || framesWithFace < 3) {
    return { descriptor: null, blinkDetected: false, framesWithFace }
  }

  return {
    descriptor: Array.from(bestDetection.descriptor),
    blinkDetected,
    framesWithFace,
  }
}