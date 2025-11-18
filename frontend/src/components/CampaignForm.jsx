import { useState } from 'react'
import './CampaignForm.css'

function CampaignForm({ onGenerate, initialData = null }) {
  const [products, setProducts] = useState(
    initialData?.products || ['', '']
  )
  const [targetMarket, setTargetMarket] = useState(
    initialData?.target_market || 'US'
  )
  const [targetAudience, setTargetAudience] = useState(
    initialData?.target_audience || ''
  )
  const [brandName, setBrandName] = useState(
    initialData?.brand_name || ''
  )
  const [campaignMessage, setCampaignMessage] = useState(
    initialData?.campaign_message || ''
  )
  const [errors, setErrors] = useState({})

  const markets = [
    'US', 'UK', 'Germany', 'France', 'Spain', 'Japan', 'China', 
    'Italy', 'Brazil', 'Canada', 'Australia', 'Netherlands', 
    'Poland', 'Russia', 'Mexico'
  ]

  const addProduct = () => {
    setProducts([...products, ''])
  }

  const removeProduct = (index) => {
    if (products.length > 2) {
      setProducts(products.filter((_, i) => i !== index))
    }
  }

  const updateProduct = (index, value) => {
    const newProducts = [...products]
    newProducts[index] = value
    setProducts(newProducts)
  }

  const validate = () => {
    const newErrors = {}
    
    const validProducts = products.filter(p => p.trim() !== '')
    if (validProducts.length < 2) {
      newErrors.products = 'At least 2 products are required'
    }

    if (!targetMarket.trim()) {
      newErrors.targetMarket = 'Target market is required'
    }

    if (!targetAudience.trim()) {
      newErrors.targetAudience = 'Target audience is required'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    
    if (!validate()) {
      return
    }

    const validProducts = products.filter(p => p.trim() !== '')
    onGenerate({
      products: validProducts,
      target_market: targetMarket,
      target_audience: targetAudience,
      brand_name: brandName.trim() || null,
      campaign_message: campaignMessage.trim() || null,
    })
  }

  return (
    <div className="campaign-form-container">
      <form className="campaign-form" onSubmit={handleSubmit}>
        <h2>{initialData ? 'Modify Your Campaign' : 'Create Your Campaign'}</h2>

        {initialData && (
          <div className="form-notice">
            <p>
              <strong>💡 Tip:</strong> Modify the fields below to avoid content filtering.
              Try changing your campaign message, product names, or target audience.
            </p>
          </div>
        )}

        <div className="form-section">
          <label className="form-label">
            Products <span className="required">*</span>
            <span className="form-hint">At least 2 products required</span>
          </label>
          {products.map((product, index) => (
            <div key={index} className="product-input-group">
              <input
                type="text"
                value={product}
                onChange={(e) => updateProduct(index, e.target.value)}
                placeholder={`Product ${index + 1}`}
                className="form-input"
              />
              {products.length > 2 && (
                <button
                  type="button"
                  onClick={() => removeProduct(index)}
                  className="btn-remove"
                  aria-label="Remove product"
                >
                  ×
                </button>
              )}
            </div>
          ))}
          <button
            type="button"
            onClick={addProduct}
            className="btn-add-product"
          >
            + Add Product
          </button>
          {errors.products && <span className="error-message">{errors.products}</span>}
        </div>

        <div className="form-section">
          <label className="form-label">
            Target Market <span className="required">*</span>
          </label>
          <select
            value={targetMarket}
            onChange={(e) => setTargetMarket(e.target.value)}
            className="form-input"
          >
            {markets.map(market => (
              <option key={market} value={market}>{market}</option>
            ))}
          </select>
          {errors.targetMarket && <span className="error-message">{errors.targetMarket}</span>}
        </div>

        <div className="form-section">
          <label className="form-label">
            Target Audience <span className="required">*</span>
            <span className="form-hint">e.g., "ages 25-55", "young professionals"</span>
          </label>
          <input
            type="text"
            value={targetAudience}
            onChange={(e) => setTargetAudience(e.target.value)}
            placeholder="ages 25-55"
            className="form-input"
          />
          {errors.targetAudience && <span className="error-message">{errors.targetAudience}</span>}
        </div>

        <div className="form-section">
          <label className="form-label">
            Brand Name
            <span className="form-hint">Optional - will be generated if not provided</span>
          </label>
          <input
            type="text"
            value={brandName}
            onChange={(e) => setBrandName(e.target.value)}
            placeholder="Your brand name"
            className="form-input"
          />
        </div>

        <div className="form-section">
          <label className="form-label">
            Campaign Message
            <span className="form-hint">Optional - will be generated if not provided</span>
          </label>
          <input
            type="text"
            value={campaignMessage}
            onChange={(e) => setCampaignMessage(e.target.value)}
            placeholder="Your campaign slogan"
            className="form-input"
          />
        </div>

        <button type="submit" className="btn btn-primary btn-submit">
          Generate Banners
        </button>
      </form>
    </div>
  )
}

export default CampaignForm

