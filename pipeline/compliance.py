#!/usr/bin/env python3
"""
Brand Compliance Checker - Verify generated images contain brand logo and name
"""

import json
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv
import os
import replicate
from typing import List, Dict, Optional

# Load environment variables from .env file in project root
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_brand_compliance(
    image_paths: List[str],
    brand_name: str,
    campaign_message: Optional[str] = None
) -> Dict:
    """
    Check if generated images contain brand logo and name using GPT-4.1-nano vision
    
    Args:
        image_paths: List of paths to generated images (best two images)
        brand_name: Expected brand name to check for
        campaign_message: Optional campaign message to verify presence
        
    Returns:
        Dictionary with compliance results
    """
    if not image_paths:
        raise ValueError("At least one image path is required")
    
    if not brand_name:
        raise ValueError("Brand name is required")
    
    # Validate image files exist
    for img_path in image_paths:
        if not Path(img_path).exists():
            raise FileNotFoundError(f"Image not found: {img_path}")
    
    logger.info(f"Checking brand compliance for brand: '{brand_name}'")
    logger.info(f"Analyzing {len(image_paths)} image(s)...")
    
    # Prepare system prompt
    system_prompt = """You are an expert brand compliance checker for advertising banners. 
Your task is to analyze images and verify brand compliance by:
1. Detecting ALL text visible in the image (using OCR/vision capabilities)
2. Checking if the brand name appears in the detected text
3. Identifying if a brand logo is visible in the image
4. Verifying the overall brand presence and compliance

Be thorough and accurate in your analysis. Report all text you can see, even if partially visible."""

    # Build user prompt
    brand_check_instruction = f"""Brand Name to Check: "{brand_name}"

Please analyze the provided image(s) and:
1. Detect and list ALL text visible in the image(s) (use your vision capabilities to read any text in ALL languages, including non-Latin scripts like Japanese, Chinese, etc.)
2. Check if the brand name "{brand_name}" appears in the detected text (exact match or close variations)
3. Identify if a brand logo is visible in the image(s) (look for logo symbols, icons, or brand marks - separate from text)
4. Assess overall brand presence and compliance

COMPLIANCE RULES:
- The image is COMPLIANT if the brand name is present in the text, even if there is no separate logo visible
- The image is NON-COMPLIANT only if the brand name is NOT found in the text
- A logo is optional and does not affect compliance status

Return your analysis in the following JSON format:
{{
    "detected_text": ["list", "of", "all", "text", "found", "in", "image"],
    "brand_name_found": true/false,
    "brand_name_matches": ["exact", "matches", "or", "close", "variations"],
    "logo_visible": true/false,
    "logo_description": "description of logo if visible, or 'none' if not visible",
    "compliance_status": "compliant" or "non-compliant",
    "compliance_notes": "detailed explanation of compliance status"
}}"""

    if campaign_message:
        brand_check_instruction += f"""

Additionally, check if the campaign message "{campaign_message}" appears in the detected text."""

    logger.info("Sending images to GPT-4.1-nano for analysis...")
    
    # Open image files for input
    image_files = []
    try:
        for img_path in image_paths:
            img_file = open(img_path, "rb")
            image_files.append(img_file)
        
        # Prepare image_input list
        image_input = [img_file for img_file in image_files]
        
        # Stream response from GPT-4.1-nano
        full_response = ""
        for event in replicate.stream(
            "openai/gpt-4.1-nano",
            input={
                "top_p": 1,
                "prompt": brand_check_instruction,
                "messages": [],
                "image_input": image_input,
                "temperature": 0.3,  # Lower temperature for more consistent analysis
                "system_prompt": system_prompt,
                "presence_penalty": 0,
                "frequency_penalty": 0,
                "max_completion_tokens": 2048,
                "response_format": {"type": "json_object"}
            },
        ):
            full_response += str(event)
        
        # Parse JSON response
        full_response = full_response.strip()
        
        # Try to extract JSON from response
        import re
        json_match = re.search(r'\{.*\}', full_response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_str = full_response
        
        # Clean up common JSON formatting issues
        json_str = re.sub(r'""([,\}])', r'"\1', json_str)
        
        try:
            result = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"Could not parse JSON response: {e}")
            logger.warning(f"Raw response: {full_response[:500]}")
            # Return a fallback result
            result = {
                "detected_text": [],
                "brand_name_found": False,
                "brand_name_matches": [],
                "logo_visible": False,
                "logo_description": "Unable to parse response",
                "compliance_status": "unknown",
                "compliance_notes": f"Failed to parse GPT response: {str(e)}"
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Error during brand compliance check: {str(e)}")
        raise
    finally:
        # Close all image files
        for img_file in image_files:
            try:
                img_file.close()
            except Exception:
                pass


def main():
    """Main function to run brand compliance check"""
    
    # Check for API token
    api_token = os.getenv("REPLICATE_API_TOKEN")
    if not api_token:
        logger.error("REPLICATE_API_TOKEN not found in .env file")
        sys.exit(1)
    
    # Example usage - can be modified to accept command line arguments
    if len(sys.argv) < 3:
        logger.info("Usage: python check_brand_compliance.py <image1> <image2> <brand_name> [campaign_message]")
        logger.info("")
        logger.info("Example:")
        logger.info('  python check_brand_compliance.py outputs/banner1.png outputs/banner2.png "TrailCraft" "Run Further"')
        sys.exit(1)
    
    # Parse arguments
    image_paths = sys.argv[1:-1] if len(sys.argv) > 3 else [sys.argv[1]]
    brand_name = sys.argv[-1] if len(sys.argv) >= 3 else sys.argv[1]
    
    # If campaign message is provided as last arg, adjust
    if len(sys.argv) >= 4:
        # Check if last arg looks like a brand name (short) vs campaign message (longer)
        # For simplicity, assume format: image1 image2 brand_name [campaign_message]
        if len(sys.argv) == 5:
            image_paths = [sys.argv[1], sys.argv[2]]
            brand_name = sys.argv[3]
            campaign_message = sys.argv[4]
        elif len(sys.argv) == 4:
            image_paths = [sys.argv[1], sys.argv[2]]
            brand_name = sys.argv[3]
            campaign_message = None
        else:
            image_paths = [sys.argv[1]]
            brand_name = sys.argv[2]
            campaign_message = None
    else:
        campaign_message = None
    
    try:
        # Run compliance check
        result = check_brand_compliance(
            image_paths=image_paths,
            brand_name=brand_name,
            campaign_message=campaign_message
        )
        
        # Print results
        logger.info("")
        logger.info("="*60)
        logger.info("BRAND COMPLIANCE CHECK RESULTS")
        logger.info("="*60)
        logger.info(f"Brand Name: {brand_name}")
        logger.info(f"Images Analyzed: {len(image_paths)}")
        logger.info("")
        logger.info("Detected Text:")
        for text in result.get("detected_text", []):
            logger.info(f"  - {text}")
        logger.info("")
        logger.info(f"Brand Name Found: {result.get('brand_name_found', False)}")
        if result.get("brand_name_matches"):
            logger.info(f"Brand Name Matches: {', '.join(result.get('brand_name_matches', []))}")
        logger.info(f"Logo Visible: {result.get('logo_visible', False)}")
        logger.info(f"Logo Description: {result.get('logo_description', 'N/A')}")
        logger.info("")
        logger.info(f"Compliance Status: {result.get('compliance_status', 'unknown').upper()}")
        logger.info(f"Notes: {result.get('compliance_notes', 'N/A')}")
        logger.info("="*60)
        
        # Return exit code based on compliance
        if result.get("compliance_status") == "compliant":
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

