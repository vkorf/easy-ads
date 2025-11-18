"""Image Generator - Generate images via Replicate API"""

import io
import time
import logging
import requests
from typing import Optional
from PIL import Image
import replicate

logger = logging.getLogger(__name__)


class GeneratorError(Exception):
    """Custom exception for generator errors"""
    pass


class ReplicateGenerator:
    """Generate images using Replicate Seedream-4 API"""

    # Model configuration
    MODEL_ID = "bytedance/seedream-4"

    # Aspect ratio mapping (seedream-4 uses different format)
    ASPECT_RATIOS = {
        "1:1": "1:1",
        "9:16": "9:16",
        "16:9": "16:9",
        "3:2": "3:2",
        "4:3": "4:3",
        "2:3": "2:3"
    }

    def __init__(self, api_token: str):
        """
        Initialize Replicate generator

        Args:
            api_token: Replicate API token
        """
        self.api_token = api_token

        # Set Replicate API token as environment variable
        import os
        os.environ["REPLICATE_API_TOKEN"] = api_token

        logger.info(f"Initialized Replicate generator with model: {self.MODEL_ID}")

    def generate(self, prompt: str, width: Optional[int] = None, height: Optional[int] = None,
                 max_retries: int = 1, aspect_ratio: str = "1:1", image_input: Optional[list] = None) -> Image.Image:
        """
        Generate image from prompt using Replicate Seedream-4

        Args:
            prompt: Text prompt for image generation
            width: Image width (ignored, uses aspect_ratio instead)
            height: Image height (ignored, uses aspect_ratio instead)
            max_retries: Maximum number of retry attempts
            aspect_ratio: Aspect ratio for the image (default: "1:1")
            image_input: Optional list of image file paths to use as reference

        Returns:
            Generated PIL Image

        Raises:
            GeneratorError: If generation fails after retries
        """
        # Validate aspect ratio
        if aspect_ratio not in self.ASPECT_RATIOS:
            logger.warning(f"Invalid aspect ratio {aspect_ratio}, defaulting to 1:1")
            aspect_ratio = "1:1"

        if image_input:
            logger.info(f"Generating image with {len(image_input)} reference image(s) and aspect ratio {aspect_ratio}: {prompt[:50]}...")
        else:
            logger.info(f"Generating image with aspect ratio {aspect_ratio}: {prompt[:50]}...")

        return self._generate_with_replicate(prompt, aspect_ratio, max_retries, image_input)

    def _generate_with_replicate(self, prompt: str, aspect_ratio: str, max_retries: int, image_input: Optional[list] = None) -> Image.Image:
        """Generate using Replicate Seedream-4 API"""
        file_handles = []  # Track file handles for cleanup
        try:
            for attempt in range(max_retries):
                try:
                    # Build input parameters
                    input_params = {
                        "prompt": prompt,
                        "aspect_ratio": aspect_ratio,
                        "size": "2K",
                        "width": 2048,
                        "height": 2048,
                        "max_images": 1,
                        "enhance_prompt": True,
                        "sequential_image_generation": "disabled"
                    }

                    # Add image_input if provided
                    if image_input and len(image_input) > 0:
                        # Open image files and pass them as file handles
                        input_params["image_input"] = []
                        for img_path in image_input:
                            fh = open(img_path, "rb")
                            file_handles.append(fh)
                            input_params["image_input"].append(fh)

                    # Run Replicate model with seedream-4 parameters
                    output = replicate.run(
                        self.MODEL_ID,
                        input=input_params
                    )

                    # Seedream-4 returns a list of FileOutput objects
                    if isinstance(output, list) and len(output) > 0:
                        item = output[0]
                        # Use the url() method for seedream-4
                        if hasattr(item, 'url'):
                            if callable(item.url):
                                image_url = item.url()
                            else:
                                image_url = item.url
                        elif isinstance(item, str):
                            image_url = item
                        else:
                            raise GeneratorError(f"Unexpected list item format: {type(item)}")
                    elif hasattr(output, 'url'):
                        if callable(output.url):
                            image_url = output.url()
                        else:
                            image_url = output.url
                    elif isinstance(output, str):
                        image_url = output
                    else:
                        raise GeneratorError(f"Unexpected output format: {type(output)}")

                    # Fetch and convert to PIL Image
                    response = requests.get(image_url, timeout=30)
                    response.raise_for_status()
                    image = Image.open(io.BytesIO(response.content))

                    logger.info(f"Successfully generated image with aspect ratio {aspect_ratio}")
                    return image

                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"Generation error (attempt {attempt + 1}/{max_retries}): {error_msg}")

                    # Check for sensitive content flag
                    if "flagged as sensitive" in error_msg.lower() or "e005" in error_msg.lower():
                        logger.error("=" * 60)
                        logger.error("SENSITIVE CONTENT DETECTED")
                        logger.error("=" * 60)
                        logger.error("The input prompt or generated output was flagged as containing sensitive content.")
                        logger.error("This could be due to:")
                        logger.error("  - Campaign message or product names containing inappropriate content")
                        logger.error("  - Generated prompt triggering content filters")
                        logger.error("  - Output image containing flagged content")
                        logger.error("")
                        logger.error("Suggestion: Review the campaign brief and modify:")
                        logger.error("  - Campaign message")
                        logger.error("  - Product names")
                        logger.error("  - Target audience description")
                        logger.error("=" * 60)
                        raise GeneratorError("Content flagged as sensitive. Please review and modify the campaign brief.")

                    # Check for rate limiting
                    elif "rate" in error_msg.lower() or "429" in error_msg:
                        wait_time = 30
                        logger.warning(f"Rate limited, waiting {wait_time}s")
                        time.sleep(wait_time)

                    # Check for authentication errors
                    elif "token" in error_msg.lower() or "401" in error_msg or "authentication" in error_msg.lower():
                        raise GeneratorError("Invalid Replicate API token")

                    # Generic error handling
                    else:
                        if attempt == max_retries - 1:
                            raise GeneratorError(f"Generation failed: {error_msg}")
                        time.sleep(2 ** attempt)

            raise GeneratorError("Failed to generate image after all retries")
        finally:
            # Close all file handles
            for fh in file_handles:
                try:
                    fh.close()
                except Exception:
                    pass  # Ignore errors during cleanup