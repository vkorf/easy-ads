import { useState } from 'react'
import './ImageGallery.css'

function ImageGallery({ images, apiBaseUrl, brandName, campaignMessage }) {
  const [selectedAspectRatio, setSelectedAspectRatio] = useState(null)
  const [complianceLoading, setComplianceLoading] = useState({})
  const [complianceResults, setComplianceResults] = useState({})
  const [complianceErrors, setComplianceErrors] = useState({})

  if (!images || images.length === 0) {
    return (
      <div className="gallery-empty">
        <p>No images generated yet.</p>
      </div>
    )
  }

  const aspectRatios = [...new Set(images.map(img => img.aspect_ratio))]

  const getImageUrl = (image) => {
    // Construct full URL
    if (image.url) {
      return `${apiBaseUrl}${image.url}`
    }
    if (image.path) {
      return `${apiBaseUrl}/outputs/${image.path}`
    }
    return null
  }

  const filteredImages = selectedAspectRatio
    ? images.filter(img => img.aspect_ratio === selectedAspectRatio)
    : images

  const handleCheckCompliance = async (imagePath, imageIndex) => {
    if (!brandName || !imagePath) {
      setComplianceErrors(prev => ({
        ...prev,
        [imageIndex]: 'Missing brand name or image'
      }))
      return
    }

    setComplianceLoading(prev => ({ ...prev, [imageIndex]: true }))
    setComplianceErrors(prev => ({ ...prev, [imageIndex]: null }))
    setComplianceResults(prev => ({ ...prev, [imageIndex]: null }))

    try {
      const response = await fetch(`${apiBaseUrl}/api/check-compliance`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          image_paths: [imagePath],
          brand_name: brandName,
          campaign_message: campaignMessage
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to check compliance')
      }

      const result = await response.json()
      setComplianceResults(prev => ({ ...prev, [imageIndex]: result }))
    } catch (err) {
      console.error('Error checking compliance:', err)
      setComplianceErrors(prev => ({ ...prev, [imageIndex]: err.message }))
    } finally {
      setComplianceLoading(prev => ({ ...prev, [imageIndex]: false }))
    }
  }

  return (
    <div className="gallery-container">
      {aspectRatios.length > 1 && (
        <div className="gallery-filters">
          <button
            className={`filter-btn ${selectedAspectRatio === null ? 'active' : ''}`}
            onClick={() => setSelectedAspectRatio(null)}
          >
            All ({images.length})
          </button>
          {aspectRatios.map(ratio => {
            const count = images.filter(img => img.aspect_ratio === ratio).length
            return (
              <button
                key={ratio}
                className={`filter-btn ${selectedAspectRatio === ratio ? 'active' : ''}`}
                onClick={() => setSelectedAspectRatio(ratio)}
              >
                {ratio} ({count})
              </button>
            )
          })}
        </div>
      )}

      <div className="gallery-grid">
        {filteredImages.map((image, index) => {
          const imageUrl = getImageUrl(image)
          if (!imageUrl) return null

          return (
            <div key={index} className="gallery-item">
              <div className="gallery-item-header">
                <span className="aspect-ratio-badge">{image.aspect_ratio}</span>
                {image.size && (
                  <span className="size-badge">{image.size[0]} × {image.size[1]}</span>
                )}
              </div>
              <div className="gallery-item-image">
                <img
                  src={imageUrl}
                  alt={`Banner ${image.aspect_ratio}`}
                  loading="lazy"
                />
              </div>
              <div className="gallery-item-actions">
                <a
                  href={imageUrl}
                  download
                  className="btn-download"
                >
                  Download
                </a>
                {brandName && (
                  <button
                    onClick={() => handleCheckCompliance(image.path, index)}
                    disabled={complianceLoading[index]}
                    className="btn-compliance"
                  >
                    {complianceLoading[index] ? 'Checking...' : 'Check Brand Compliance'}
                  </button>
                )}
              </div>

              {complianceErrors[index] && (
                <div className="compliance-error">
                  <span className="error-icon">❌</span>
                  <p>{complianceErrors[index]}</p>
                </div>
              )}

              {complianceResults[index] && (
                <div className={`compliance-result ${complianceResults[index].compliance_status === 'compliant' ? 'compliant' : 'non-compliant'}`}>
                  <div className="compliance-header">
                    <span className="compliance-icon">
                      {complianceResults[index].compliance_status === 'compliant' ? '✅' : '⚠️'}
                    </span>
                    <h3>Compliance: {complianceResults[index].compliance_status?.toUpperCase()}</h3>
                  </div>

                  <div className="compliance-details">
                    <div className="compliance-item">
                      <strong>Brand Name:</strong> {complianceResults[index].brand_name_found ? 'Yes' : 'No'}
                    </div>
                    <div className="compliance-item">
                      <strong>Logo:</strong> {complianceResults[index].logo_visible ? 'Yes' : 'No'}
                    </div>
                    {complianceResults[index].logo_description && (
                      <div className="compliance-item">
                        <strong>Description:</strong> {complianceResults[index].logo_description}
                      </div>
                    )}
                    {complianceResults[index].detected_text && complianceResults[index].detected_text.length > 0 && (
                      <div className="compliance-item">
                        <strong>Text:</strong> {complianceResults[index].detected_text.join(', ')}
                      </div>
                    )}
                    {complianceResults[index].compliance_notes && (
                      <div className="compliance-item">
                        <strong>Notes:</strong> {complianceResults[index].compliance_notes}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default ImageGallery

