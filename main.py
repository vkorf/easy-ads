#!/usr/bin/env python3
"""
Simplified Creative Automation - Generate single banner with 2 products
"""

import json
import logging
from pathlib import Path
from dotenv import load_dotenv
import os
from datetime import datetime

from pipeline.generator import ReplicateGenerator
from pipeline.assets_loader import AssetsLoader
from pipeline.reporter import PipelineReporter
from pipeline.campaign_utils import (
    generate_optimized_prompt,
    validate_campaign,
    LegalComplianceError
)

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    # Load campaign brief
    brief_path = "examples/campaign.json"
    logger.info(f"Loading campaign: {brief_path}")

    with open(brief_path) as f:
        campaign = json.load(f)

    # Initialize pipeline reporter
    reporter = PipelineReporter(campaign)

    # Validate campaign brief
    reporter.start_step("Campaign Validation", {
        "brief_path": brief_path
    })
    try:
        validate_campaign(campaign)
        reporter.end_step("success")
    except Exception as e:
        reporter.end_step("failed", error_message=str(e))
        reporter.finalize("failed")
        raise

    # Load assets from assets folder
    reporter.start_step("Load Assets", {
        "assets_directory": "assets"
    })
    try:
        assets_loader = AssetsLoader(assets_dir="assets")

        # Load text assets
        assets = assets_loader.load_all_text_assets()

        # Format assets for prompt enrichment
        assets_context = ""
        if assets:
            assets_context = assets_loader.format_assets_for_prompt(assets)
            logger.info("Text assets loaded successfully:")
            logger.info(assets_loader.get_assets_summary(assets))
        else:
            logger.info("No text assets found to enrich prompts")

        reporter.end_step("success", {
            "text_assets_count": len(assets)
        })
    except Exception as e:
        reporter.end_step("failed", error_message=str(e))
        reporter.finalize("failed")
        raise

    # Get API token
    api_token = os.getenv("REPLICATE_API_TOKEN")
    if not api_token:
        logger.error("REPLICATE_API_TOKEN not found in .env file")
        reporter.finalize("failed")
        return

    # Initialize generator
    reporter.start_step("Initialize Generator", {
        "model": "bytedance/seedream-4"
    })
    try:
        generator = ReplicateGenerator(api_token)
        reporter.end_step("success")
    except Exception as e:
        reporter.end_step("failed", error_message=str(e))
        reporter.finalize("failed")
        raise

    # Extract campaign details for logging
    products = campaign.get("products", [])
    target_market = campaign.get("target_market", "US")
    target_audience = campaign.get("target_audience", "")
    campaign_message = campaign.get("campaign_message", "")
    brand_name = campaign.get("brand_name", "").strip()

    # Build product descriptions for logging (simple strings)
    products_text = ", ".join([str(p) for p in products])

    logger.info("="*60)
    logger.info("CAMPAIGN BRIEF")
    logger.info("="*60)
    logger.info(f"  Brand: {brand_name if brand_name else '(to be generated)'}")
    logger.info(f"  Products: {products_text}")
    logger.info(f"  Target Market: {target_market}")
    logger.info(f"  Target Audience: {target_audience}")
    logger.info(f"  Campaign Message: {campaign_message}")
    logger.info("="*60)
    logger.info("")

    # Use GPT-4 to generate optimized prompt with assets context
    # This includes legal compliance checking for prohibited words
    reporter.start_step("Generate Optimized Prompt", {
        "model": "GPT-4",
        "has_assets": bool(assets_context)
    })
    try:
        prompt, translated_message = generate_optimized_prompt(campaign, assets_context, has_reference_images=False)
        logger.info("OPTIMIZED PROMPT (GPT-4):")
        logger.info(prompt)
        logger.info("")
        reporter.end_step("success", {
            "prompt_length": len(prompt),
            "translated_message": translated_message
        })
    except LegalComplianceError as e:
        # Special handling for legal compliance errors
        logger.error("")
        logger.error("Campaign rejected due to legal compliance violations.")
        logger.error(f"Prohibited words found: {', '.join(e.prohibited_words_found)}")
        logger.error("Please revise your campaign brief and try again.")
        logger.error("")
        reporter.end_step("failed", error_message=str(e))
        reporter.finalize("failed")
        raise
    except Exception as e:
        reporter.end_step("failed", error_message=str(e))
        reporter.finalize("failed")
        raise

    # Generate images for all aspect ratios
    aspect_ratios = ["1:1", "9:16", "16:9"]
    generated_images = []

    # Create output directory structure
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_output_dir = Path("outputs") / f"{target_market.lower().replace(' ', '_')}_{timestamp}"
    base_output_dir.mkdir(parents=True, exist_ok=True)

    for aspect_ratio in aspect_ratios:
        reporter.start_step(f"Generate {aspect_ratio} Image", {
            "model": "Seedream-4",
            "aspect_ratio": aspect_ratio
        })
        try:
            # Generate image with specific aspect ratio
            image = generator.generate(prompt, aspect_ratio=aspect_ratio, image_input=None)
            reporter.end_step("success", {
                "image_size": f"{image.size[0]}x{image.size[1]}",
                "image_mode": image.mode
            })

            # Save output
            reporter.start_step(f"Save {aspect_ratio} Output", {
                "output_directory": str(base_output_dir),
                "aspect_ratio": aspect_ratio
            })

            # Create aspect ratio subdirectory
            aspect_dir = base_output_dir / aspect_ratio.replace(':', '_')
            aspect_dir.mkdir(exist_ok=True)

            # Save image
            output_filename = f"banner_{target_market.lower().replace(' ', '_')}.png"
            output_path = aspect_dir / output_filename
            image.save(output_path)

            logger.info("")
            logger.info(f"  Saved {aspect_ratio} to: {output_path}")
            logger.info(f"  Size: {image.size}")
            logger.info("")

            reporter.add_output_file(str(output_path))
            reporter.end_step("success", {
                "output_path": str(output_path),
                "file_size_bytes": output_path.stat().st_size,
                "aspect_ratio": aspect_ratio
            })

            generated_images.append(output_path)

        except Exception as e:
            reporter.end_step("failed", error_message=str(e))
            logger.error(f"Failed to generate {aspect_ratio} banner: {str(e)}")
            # Continue with other aspect ratios instead of failing completely
            continue

    # Check if at least one image was generated
    if len(generated_images) == 0:
        reporter.finalize("failed")
        raise Exception("All image generations failed")

    # Finalize report
    reporter.finalize("completed")


if __name__ == "__main__":
    main()
