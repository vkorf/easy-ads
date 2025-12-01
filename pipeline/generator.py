"""Image Generator - Generate images via AtlasCloud API"""

import io
import time
import logging
import requests
from typing import Optional
from PIL import Image

logger = logging.getLogger(__name__)


class GeneratorError(Exception):
    """Custom exception for generator errors"""
    pass


class AtlasCloudGenerator:
    """Generate images using AtlasCloud Seedream-v4 API"""

    # Model configuration
    MODEL_ID = "bytedance/seedream-v4"
    GENERATE_URL = "https://api.atlascloud.ai/api/v1/model/generateImage"
    POLL_URL_TEMPLATE = "https://api.atlascloud.ai/api/v1/model/prediction/{prediction_id}"

    # Aspect ratio mapping to size format
    ASPECT_RATIOS = {
        "1:1": "2048*2048",
        "9:16": "1152*2048",
        "16:9": "2048*1152",
        "3:2": "2048*1365",
        "4:3": "2048*1536",
        "2:3": "1365*2048"
    }

    def __init__(self, api_token: str):
        """
        Initialize AtlasCloud generator

        Args:
            api_token: AtlasCloud API token
        """
        self.api_token = api_token
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_token}"
        }

        logger.info(f"Initialized AtlasCloud generator with model: {self.MODEL_ID}")

    def generate(self, prompt: str, width: Optional[int] = None, height: Optional[int] = None,
                 max_retries: int = 1, aspect_ratio: str = "1:1", image_input: Optional[list] = None) -> Image.Image:
        """
        Generate image from prompt using AtlasCloud Seedream-v4

        Args:
            prompt: Text prompt for image generation
            width: Image width (ignored, uses aspect_ratio instead)
            height: Image height (ignored, uses aspect_ratio instead)
            max_retries: Maximum number of retry attempts
            aspect_ratio: Aspect ratio for the image (default: "1:1")
            image_input: Optional list of image file paths to use as reference (not supported yet)

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
            logger.warning("Image input references are not yet supported with AtlasCloud API")

        logger.info(f"Generating image with aspect ratio {aspect_ratio}: {prompt[:50]}...")

        return self._generate_with_atlascloud(prompt, aspect_ratio, max_retries)

    def _generate_with_atlascloud(self, prompt: str, aspect_ratio: str, max_retries: int) -> Image.Image:
        """Generate using AtlasCloud Seedream-v4 API"""
        for attempt in range(max_retries):
            try:
                # Step 1: Start image generation
                size = self.ASPECT_RATIOS[aspect_ratio]
                data = {
                    "model": self.MODEL_ID,
                    "enable_base64_output": False,
                    "enable_sync_mode": False,
                    "prompt": prompt,
                    "size": size
                }

                logger.info(f"Starting image generation (attempt {attempt + 1}/{max_retries})...")
                generate_response = requests.post(
                    self.GENERATE_URL,
                    headers=self.headers,
                    json=data,
                    timeout=30
                )
                generate_response.raise_for_status()
                generate_result = generate_response.json()

                # Check for errors in response
                if "error" in generate_result or generate_result.get("code") != 200:
                    error_msg = generate_result.get("error", generate_result.get("message", "Unknown error"))
                    raise GeneratorError(f"API error: {error_msg}")

                prediction_id = generate_result["data"]["id"]
                logger.info(f"Generation started with prediction ID: {prediction_id}")

                # Step 2: Poll for result
                image_url = self._poll_for_result(prediction_id)

                # Step 3: Fetch and convert to PIL Image
                logger.info(f"Downloading generated image...")
                response = requests.get(image_url, timeout=60)
                response.raise_for_status()
                image = Image.open(io.BytesIO(response.content))

                logger.info(f"Successfully generated image with aspect ratio {aspect_ratio}")
                return image

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Generation error (attempt {attempt + 1}/{max_retries}): {error_msg}")

                # Check for sensitive content flag
                if "sensitive" in error_msg.lower() or "nsfw" in error_msg.lower():
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
                elif "token" in error_msg.lower() or "401" in error_msg or "authentication" in error_msg.lower() or "unauthorized" in error_msg.lower():
                    raise GeneratorError("Invalid AtlasCloud API token")

                # Generic error handling
                else:
                    if attempt == max_retries - 1:
                        raise GeneratorError(f"Generation failed: {error_msg}")
                    time.sleep(2 ** attempt)

        raise GeneratorError("Failed to generate image after all retries")

    def _poll_for_result(self, prediction_id: str, poll_interval: int = 2, max_wait: int = 300) -> str:
        """
        Poll for generation result

        Args:
            prediction_id: The prediction ID to poll
            poll_interval: Seconds between polls (default: 2)
            max_wait: Maximum seconds to wait (default: 300 = 5 minutes)

        Returns:
            URL of generated image

        Raises:
            GeneratorError: If generation fails or times out
        """
        poll_url = self.POLL_URL_TEMPLATE.format(prediction_id=prediction_id)
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > max_wait:
                raise GeneratorError(f"Generation timed out after {max_wait} seconds")

            try:
                response = requests.get(
                    poll_url,
                    headers={"Authorization": f"Bearer {self.api_token}"},
                    timeout=30
                )
                response.raise_for_status()
                result = response.json()

                # Check for API errors
                if "error" in result or result.get("code") != 200:
                    error_msg = result.get("error", result.get("message", "Unknown error"))
                    raise GeneratorError(f"API error: {error_msg}")

                status = result["data"]["status"]
                logger.debug(f"Status: {status} (elapsed: {elapsed:.1f}s)")

                if status == "completed":
                    outputs = result["data"].get("outputs", [])
                    if not outputs:
                        raise GeneratorError("No outputs in completed result")
                    image_url = outputs[0]
                    logger.info(f"Generation completed in {elapsed:.1f}s")
                    return image_url

                elif status == "failed":
                    error = result["data"].get("error", "Generation failed")
                    raise GeneratorError(error)

                else:
                    # Still processing, wait before next poll
                    time.sleep(poll_interval)

            except requests.exceptions.RequestException as e:
                logger.warning(f"Poll request failed: {e}, retrying...")
                time.sleep(poll_interval)


# Backwards compatibility alias
ReplicateGenerator = AtlasCloudGenerator
