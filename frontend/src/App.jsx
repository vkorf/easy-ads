import { useState, useEffect } from 'react'
import CampaignForm from './components/CampaignForm'
import ImageGallery from './components/ImageGallery'
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const [jobId, setJobId] = useState(null)
  const [jobStatus, setJobStatus] = useState(null)
  const [generatedImages, setGeneratedImages] = useState(null)
  const [error, setError] = useState(null)
  const [lastCampaignData, setLastCampaignData] = useState(null)

  // Poll for job status
  useEffect(() => {
    if (!jobId) return

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/status/${jobId}`)
        if (!response.ok) throw new Error('Failed to fetch status')
        
        const status = await response.json()
        setJobStatus(status)

        if (status.status === 'completed') {
          clearInterval(pollInterval)
          // Fetch images
          const imagesResponse = await fetch(`${API_BASE_URL}/api/images/${jobId}`)
          if (imagesResponse.ok) {
            const images = await imagesResponse.json()
            setGeneratedImages(images)
          }
        } else if (status.status === 'failed') {
          clearInterval(pollInterval)
          setError({
            message: status.error || 'Generation failed',
            isSensitiveContent: status.error && status.error.includes('sensitive')
          })
        }
      } catch (err) {
        console.error('Error polling status:', err)
        clearInterval(pollInterval)
        setError({
          message: err.message,
          isSensitiveContent: false
        })
      }
    }, 2000) // Poll every 2 seconds

    return () => clearInterval(pollInterval)
  }, [jobId])

  const handleGenerate = async (campaignData) => {
    setError(null)
    setJobStatus(null)
    setGeneratedImages(null)
    setLastCampaignData(campaignData)

    try {
      const response = await fetch(`${API_BASE_URL}/api/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(campaignData),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to start generation')
      }

      const result = await response.json()
      setJobId(result.job_id)
      setJobStatus({ status: 'pending', progress: null })
    } catch (err) {
      setError({
        message: err.message,
        isSensitiveContent: false
      })
      console.error('Error starting generation:', err)
    }
  }

  const handleReset = (clearData = true) => {
    setJobId(null)
    setJobStatus(null)
    setGeneratedImages(null)
    setError(null)
    if (clearData) {
      setLastCampaignData(null)
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title">Easy Ads</h1>
        <p className="app-subtitle">AI-Powered Banner Generation</p>
      </header>

      <main className="app-main">
        {!jobId && !generatedImages && !error && (
          <CampaignForm onGenerate={handleGenerate} />
        )}

        {jobId && jobStatus && jobStatus.status !== 'completed' && (
          <div className="status-container">
            <div className="status-card">
              <h2>Generating Your Banners</h2>
              {jobStatus.progress && (
                <div className="progress-info">
                  <p className="progress-step">{jobStatus.progress.step}</p>
                  <div className="progress-bar">
                    <div 
                      className="progress-fill" 
                      style={{ width: `${jobStatus.progress.progress}%` }}
                    ></div>
                  </div>
                  <p className="progress-percent">{jobStatus.progress.progress}%</p>
                </div>
              )}
              {jobStatus.status === 'processing' && (
                <div className="spinner"></div>
              )}
            </div>
          </div>
        )}

        {error && (
          <div className="error-container">
            <div className={`error-card ${error.isSensitiveContent ? 'error-card-warning' : ''}`}>
              <div className="error-header">
                <span className="error-icon">
                  {error.isSensitiveContent ? '⚠️' : '❌'}
                </span>
                <h2>{error.isSensitiveContent ? 'Content Flagged' : 'Error'}</h2>
              </div>

              {error.isSensitiveContent ? (
                <div className="error-details">
                  <p className="error-message-main">
                    The input or output was flagged as containing sensitive content.
                  </p>

                  <div className="error-suggestions">
                    <p className="error-suggestions-title">This could be due to:</p>
                    <ul>
                      <li>Campaign message containing inappropriate words</li>
                      <li>Product names triggering content filters</li>
                      <li>Generated output containing flagged content</li>
                    </ul>
                  </div>

                  <div className="error-suggestions">
                    <p className="error-suggestions-title">Please try modifying:</p>
                    <ul>
                      <li>Your campaign message to use different wording</li>
                      <li>Product names to be more descriptive</li>
                      <li>Target audience description</li>
                    </ul>
                  </div>

                  <div className="error-actions">
                    <button
                      onClick={() => handleReset(false)}
                      className="btn btn-primary"
                    >
                      Modify Campaign & Retry
                    </button>
                    <button
                      onClick={() => handleReset(true)}
                      className="btn btn-secondary"
                    >
                      Start Over
                    </button>
                  </div>
                </div>
              ) : (
                <div className="error-details">
                  <p className="error-message-main">{error.message}</p>
                  <div className="error-actions">
                    <button onClick={() => handleReset(true)} className="btn btn-secondary">
                      Try Again
                    </button>
                  </div>
                </div>
              )}
            </div>

            {error.isSensitiveContent && lastCampaignData && (
              <div className="retry-form-container">
                <CampaignForm
                  onGenerate={handleGenerate}
                  initialData={lastCampaignData}
                />
              </div>
            )}
          </div>
        )}

        {generatedImages && (
          <div className="results-container">
            <div className="results-header">
              <div>
                <h2>Your Banners Are Ready!</h2>
                {generatedImages.brand_name && (
                  <p className="brand-info">Brand: <strong>{generatedImages.brand_name}</strong></p>
                )}
                {generatedImages.campaign_message && (
                  <p className="campaign-info">Message: <strong>{generatedImages.campaign_message}</strong></p>
                )}
              </div>
              <button onClick={handleReset} className="btn btn-primary">
                Create New Campaign
              </button>
            </div>
            <ImageGallery
              images={generatedImages.images}
              apiBaseUrl={API_BASE_URL}
              brandName={generatedImages.brand_name}
              campaignMessage={generatedImages.translated_campaign_message || generatedImages.campaign_message}
            />
          </div>
        )}
      </main>
    </div>
  )
}

export default App
