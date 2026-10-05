import { useEffect, useRef, useState } from 'react'
import { loadFaceModels, captureAveragedDescriptor } from '../services/faceapi'

export default function FaceCapture({ buttonLabel = 'Capture', helperText, onDescriptor }) {
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const [ready, setReady] = useState(false)
  const [error, setError] = useState('')
  const [capturing, setCapturing] = useState(false)

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
    try {
      const descriptor = await captureAveragedDescriptor(videoRef.current)
      if (!descriptor) {
        setError('No face detected. Centre your face in the frame, make sure lighting is good, and try again.')
        return
      }
      await onDescriptor(descriptor)
    } catch (err) {
      setError('Face capture failed unexpectedly. Please try again.')
    } finally {
      setCapturing(false)
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
      </div>

      {helperText && <p className="text-muted" style={{ fontSize: 12, marginTop: -8 }}>{helperText}</p>}
      {error && <div className="auth-error">{error}</div>}

      <button className="btn btn-primary" disabled={!ready || capturing} onClick={capture}>
        {capturing ? 'Verifying…' : buttonLabel}
      </button>
    </div>
  )
}