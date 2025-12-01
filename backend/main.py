"""
FastAPI backend for Easy Ads - Image Generation API
"""

import os
import sys
import json
import logging
import uuid
from pathlib import Path
from typing import Optional, List
from datetime import datetime

# Add project root to Python path before importing local modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from pipeline.generator import AtlasCloudGenerator
from pipeline.assets_loader import AssetsLoader

# Import compliance checker
from pipeline.compliance import check_brand_compliance

# Import campaign utility functions
from pipeline.campaign_utils import (
    generate_optimized_prompt,
    generate_brand_name,
    generate_campaign_message,
    validate_campaign
)

# Load environment variables from project root
load_dotenv(dotenv_path=project_root / ".env")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Easy Ads API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:5174", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for generation jobs (in production, use Redis or database)
generation_jobs = {}

# Mount static files for serving generated images
outputs_dir = project_root / "outputs"
outputs_dir.mkdir(exist_ok=True)
app.mount("/outputs", StaticFiles(directory=str(outputs_dir)), name="outputs")


# Pydantic models
class CampaignRequest(BaseModel):
    products: List[str] = Field(..., min_length=2, description="List of at least 2 products")
    target_market: str = Field(..., description="Target market (e.g., US, UK, Germany, Japan)")
    target_audience: str = Field(..., description="Target audience description")
    brand_name: Optional[str] = Field(None, description="Brand name (optional, will be generated if not provided)")
    campaign_message: Optional[str] = Field(None, description="Campaign message/slogan (optional, will be generated if not provided)")


class GenerationResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatus(BaseModel):
    job_id: str
    status: str  # "pending", "processing", "completed", "failed"
    progress: Optional[dict] = None
    result: Optional[dict] = None
    error: Optional[str] = None


class ComplianceCheckRequest(BaseModel):
    image_paths: List[str] = Field(..., min_length=1, description="List of relative image paths")
    brand_name: str = Field(..., description="Brand name to check for")
    campaign_message: Optional[str] = Field(None, description="Campaign message to verify")


def generate_banners_task(job_id: str, campaign: dict):
    """Background task to generate banners"""
    try:
        generation_jobs[job_id]["status"] = "processing"
        generation_jobs[job_id]["progress"] = {"step": "Initializing", "progress": 0}
        
        # Validate campaign
        validate_campaign(campaign)
        
        # Extract campaign details
        products = campaign.get("products", [])
        target_market = campaign.get("target_market", "US")
        target_audience = campaign.get("target_audience", "")
        campaign_message = (campaign.get("campaign_message") or "").strip()
        brand_name = (campaign.get("brand_name") or "").strip()
        
        # Get API token
        api_token = os.getenv("ATLASCLOUD_API_KEY")
        if not api_token:
            raise ValueError("ATLASCLOUD_API_KEY not found in environment")
        
        # Generate brand_name if blank
        if not brand_name:
            generation_jobs[job_id]["progress"] = {"step": "Generating brand name", "progress": 10}
            brand_name = generate_brand_name(products, target_market, target_audience)
            campaign["brand_name"] = brand_name

        # Generate campaign_message if blank
        if not campaign_message:
            generation_jobs[job_id]["progress"] = {"step": "Generating campaign message", "progress": 20}
            campaign_message = generate_campaign_message(products, target_market, target_audience, brand_name)
            campaign["campaign_message"] = campaign_message

        # Log campaign details
        logger.info("="*80)
        logger.info("CAMPAIGN DETAILS:")
        logger.info(f"  Products: {products}")
        logger.info(f"  Target Market: {target_market}")
        logger.info(f"  Target Audience: {target_audience}")
        logger.info(f"  Brand Name: {brand_name}")
        logger.info(f"  Campaign Message (English): {campaign_message}")
        logger.info("="*80)
        
        # Load assets
        generation_jobs[job_id]["progress"] = {"step": "Loading assets", "progress": 30}
        assets_loader = AssetsLoader(assets_dir=str(project_root / "assets"))
        assets = assets_loader.load_all_text_assets()
        assets_context = ""
        if assets:
            assets_context = assets_loader.format_assets_for_prompt(assets)
        
        # Generate optimized prompt
        generation_jobs[job_id]["progress"] = {"step": "Optimizing prompt", "progress": 40}
        prompt, translated_campaign_message = generate_optimized_prompt(campaign, assets_context, has_reference_images=False)

        # Update campaign with translated message for compliance checking
        campaign["translated_campaign_message"] = translated_campaign_message

        # Log the complete prompt for debugging
        logger.info("="*80)
        logger.info("FINAL PROMPT SENT TO IMAGE GENERATION MODEL:")
        logger.info("="*80)
        logger.info(prompt)
        logger.info(f"Translated Campaign Message: {translated_campaign_message}")
        logger.info("="*80)

        # Initialize generator
        generation_jobs[job_id]["progress"] = {"step": "Initializing generator", "progress": 50}
        generator = AtlasCloudGenerator(api_token)
        
        # Generate images for each aspect ratio
        aspect_ratios = ["1:1", "9:16", "16:9"]
        aspect_ratios = ["1:1"]

        generated_images = []
        generation_errors = []

        # Create output directory
        product_folder_name = brand_name.lower().replace(' ', '_').replace('/', '_') if brand_name else str(products[0]).lower().replace(' ', '_').replace('/', '_')[:30]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_output_dir = outputs_dir / f"{product_folder_name}_{timestamp}"
        base_output_dir.mkdir(parents=True, exist_ok=True)

        for idx, aspect_ratio in enumerate(aspect_ratios):
            progress = 50 + int((idx + 1) / len(aspect_ratios) * 40)
            generation_jobs[job_id]["progress"] = {
                "step": f"Generating {aspect_ratio} banner",
                "progress": progress
            }

            try:
                # Generate image
                image = generator.generate(prompt, aspect_ratio=aspect_ratio)

                # Create aspect ratio subdirectory
                aspect_dir = base_output_dir / aspect_ratio.replace(':', '_')
                aspect_dir.mkdir(exist_ok=True)

                # Save image
                output_filename = f"banner_{target_market.lower().replace(' ', '_')}.png"
                output_path = aspect_dir / output_filename
                image.save(output_path)

                relative_path = output_path.relative_to(outputs_dir)
                generated_images.append({
                    'aspect_ratio': aspect_ratio,
                    'path': str(relative_path),
                    'url': f"/outputs/{relative_path}",
                    'size': list(image.size)
                })

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Failed to generate {aspect_ratio} banner: {error_msg}")
                generation_errors.append(error_msg)
                # Continue with other aspect ratios

        # Check if any images were generated
        if len(generated_images) == 0:
            # All generations failed
            error_message = generation_errors[0] if generation_errors else "All image generations failed"
            generation_jobs[job_id]["status"] = "failed"
            generation_jobs[job_id]["error"] = error_message
            logger.error(f"Job {job_id} failed: {error_message}")
        else:
            # At least some images generated successfully
            generation_jobs[job_id]["status"] = "completed"
            generation_jobs[job_id]["progress"] = {"step": "Complete", "progress": 100}
            generation_jobs[job_id]["result"] = {
                "brand_name": brand_name,
                "campaign_message": campaign_message,
                "translated_campaign_message": translated_campaign_message,
                "images": generated_images,
                "output_dir": str(base_output_dir.relative_to(outputs_dir))
            }
            if generation_errors:
                logger.warning(f"Job {job_id} completed with {len(generation_errors)} error(s)")
        
    except Exception as e:
        logger.error(f"Generation failed: {str(e)}")
        generation_jobs[job_id]["status"] = "failed"
        generation_jobs[job_id]["error"] = str(e)


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Easy Ads API", "version": "1.0.0"}


@app.post("/api/generate", response_model=GenerationResponse)
async def generate_campaign(campaign: CampaignRequest, background_tasks: BackgroundTasks):
    """Generate banners for a campaign"""
    try:
        # Create job
        job_id = str(uuid.uuid4())
        generation_jobs[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "progress": None,
            "result": None,
            "error": None
        }
        
        # Convert to dict
        campaign_dict = campaign.model_dump()
        
        # Start background task
        background_tasks.add_task(generate_banners_task, job_id, campaign_dict)
        
        return GenerationResponse(
            job_id=job_id,
            status="pending",
            message="Generation started"
        )
    except Exception as e:
        logger.error(f"Error starting generation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get status of a generation job"""
    if job_id not in generation_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = generation_jobs[job_id]
    return JobStatus(**job)


@app.get("/api/images/{job_id}")
async def get_job_images(job_id: str):
    """Get generated images for a job"""
    if job_id not in generation_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = generation_jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")

    return job["result"]


@app.post("/api/check-compliance")
async def check_compliance(request: ComplianceCheckRequest):
    """Check brand compliance for generated images"""
    try:
        # Convert relative paths to absolute paths
        absolute_paths = []
        for rel_path in request.image_paths:
            abs_path = outputs_dir / rel_path
            if not abs_path.exists():
                raise HTTPException(status_code=404, detail=f"Image not found: {rel_path}")
            absolute_paths.append(str(abs_path))

        # Check API token (compliance still uses OpenAI, not AtlasCloud)
        api_token = os.getenv("OPENAI_API_TOKEN")
        if not api_token:
            raise HTTPException(status_code=500, detail="OPENAI_API_TOKEN not configured")

        # Run compliance check
        logger.info(f"Running compliance check for brand: {request.brand_name}")
        logger.info(f"Checking {len(absolute_paths)} image(s)")

        result = check_brand_compliance(
            image_paths=absolute_paths,
            brand_name=request.brand_name,
            campaign_message=request.campaign_message
        )

        logger.info(f"Compliance check completed: {result.get('compliance_status', 'unknown')}")

        return result

    except FileNotFoundError as e:
        logger.error(f"File not found during compliance check: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        logger.error(f"Validation error during compliance check: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error during compliance check: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Compliance check failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

