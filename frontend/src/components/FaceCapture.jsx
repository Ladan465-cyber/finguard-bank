import { useEffect, useRef, useState } from 'react'
import { loadFaceModels, captureWithLiveness } from '../services/faceapi'

export default function FaceCapture({ buttonLabel = 'Capture', helperText, onDescriptor }) {
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const [ready, setReady] = useState(false)
  const [error, setError] = useState('')
  const [capturing, setCapturing] = useState(false)
  const [progressMessage, setProgressMessage] = useState('')

  useEffect(() => {
    let cancelled = false

    async function start() {
      try {
        await loadFaceModels()
      } catch {
        if (!cancelled) {
          setError(
            'Could not load the face verification models. Make sure ' +
            '"npm install" finished successfully (it copies model files into ' +
            'public/models automatically) and reload the page.'
          )
        }
        return
      }

      try {
        // Higher resolution than before -- produces a sharper, more
        // reliable face descriptor and reduces false matches between
        // different people.
        const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } })
        if (cancelled) {
          stream.getTracks().forEach(t => t.stop())
          return
        }
        streamRef.current = stream
        if (videoRef.current) {
          videoRef.current.srcObject = stream
          await videoRef.current.play()
        }
        setReady(true)
      } catch (err) {
        if (!cancelled) {
          setError(
            err.name === 'NotAllowedError'
              ? 'Camera access was denied. Allow camera permission in your browser and reload this page.'
              : 'Could not access your camera. Make sure no other app is using it.'
          )
        }
      }
    }

    start()
    return () => {
      cancelled = true
      streamRef.current?.getTracks().forEach(t => t.stop())
    }
  }, [])

  const capture = async () => {
    setError('')
    setCapturing(true)
    setProgressMessage('Hold still and blink naturally…')
    try {
      const { descriptor, blinkDetected, framesWithFace } = await captureWithLiveness(videoRef.current)

      if (framesWithFace < 3) {
        setError('No face detected consistently. Centre your face in the frame, make sure lighting is good, and try again.')
        return
      }
      if (!blinkDetected) {
        setError('We couldn\u2019t detect a blink, so this can\u2019t be confirmed as a live person (not a photo). Look at the camera and blink naturally, then try again.')
        return
      }
      if (!descriptor) {
        setError('Face capture failed. Please try again.')
        return
      }

      await onDescriptor(descriptor)
    } catch (err) {
      setError('Face capture failed unexpectedly. Please try again.')
    } finally {
      setCapturing(false)
      setProgressMessage('')
    }
  }

  return (
    <div>
      <div className="facial-frame" style={{ padding: 0, overflow: 'hidden', position: 'relative' }}>
        <video
          ref={videoRef}
          muted
          playsInline
          style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: 'var(--radius)', transform: 'scaleX(-1)' }}
        />
        {!ready && !error && (
          <span style={{ position: 'absolute' }}>Starting camera…</span>
        )}
        {capturing && (
          <span style={{ position: 'absolute', bottom: 10, background: 'rgba(0,0,0,0.6)', padding: '4px 10px', borderRadius: 100, fontSize: 12 }}>
            {progressMessage}
          </span>
        )}
      </div>

      {helperText && <p className="text-muted" style={{ fontSize: 12, marginTop: -8 }}>{helperText}</p>}
      {error && <div className="auth-error">{error}</div>}

      <button className="btn btn-primary" disabled={!ready || capturing} onClick={capture}>
        {capturing ? 'Analysing (please blink)…' : buttonLabel}
      </button>
    </div>
  )
}