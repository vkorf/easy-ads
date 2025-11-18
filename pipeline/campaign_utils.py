"""
Campaign utility functions for brand name generation, campaign message generation,
prompt optimization, and validation.

These functions are shared between the CLI (main.py) and the FastAPI backend.
"""

import logging
import json
import re
from typing import Tuple
from pydantic import BaseModel, Field
import replicate

logger = logging.getLogger(__name__)


class OptimizedPrompt(BaseModel):
    """Structured output for optimized advertising prompt"""
    image_prompt: str = Field(
        description="Detailed image generation prompt that includes the brand name in quotes (but NOT product names in quotes), logo placement description, and campaign message"
    )
    translated_campaign_message: str = Field(
        description="The campaign message in the target market language (as it will appear in the image)"
    )
    brand_mentions: int = Field(
        description="Number of times the brand name appears in quotes in the prompt"
    )
    includes_logo: bool = Field(
        description="Whether the prompt explicitly mentions the brand logo placement"
    )
    includes_campaign_message: bool = Field(
        description="Whether the prompt includes the campaign message text"
    )


def generate_optimized_prompt(campaign: dict, assets_context: str = "", has_reference_images: bool = False) -> Tuple[str, str]:
    """Use GPT-4 to generate optimized prompt from campaign brief with structured output

    Args:
        campaign: Campaign brief dictionary
        assets_context: Optional context from loaded assets (style guides, brainstorms, etc.)
        has_reference_images: Whether reference images are available in assets

    Returns:
        Tuple of (optimized_prompt, translated_campaign_message)
    """

    # Build system prompt from the template with Seedream 4.0 best practices
    system_prompt = """You are an expert creative strategist for advertising banners optimizing prompts for Seedream 4.0 image generation with global market expertise.

SEEDREAM 4.0 BEST PRACTICES:
1. Use coherent natural language describing: subject + action + environment
2. For text rendering: ALWAYS use double quotation marks around text that should appear in the image
3. Include specific style descriptors (color, lighting, composition) when relevant
4. Be clear and specific about the scene composition
5. Specify the application scenario (e.g., "advertising banner", "social media post")
6. Use precise style keywords for aesthetic rendering

MARKET LOCALIZATION EXPERTISE:
You are fluent in all languages and deeply understand cultural preferences for every market:
- Automatically translate ALL text elements (brand names if appropriate, campaign messages, slogans) to the target market's primary language
- Adapt visual styles, colors, and aesthetics to match cultural preferences
- Consider cultural symbolism, color meanings, and design preferences
- Adjust composition and imagery to resonate with local audiences

LANGUAGE TRANSLATION RULES:
- US/UK/Australia/Canada: English (DO NOT TRANSLATE - use original English campaign message)
- Germany/Austria/Switzerland: German (TRANSLATE campaign message to German)
- France: French (TRANSLATE campaign message to French)
- Spain/Mexico/Latin America: Spanish (TRANSLATE campaign message to Spanish)
- Japan: Japanese (TRANSLATE campaign message to Japanese)
- China: Simplified Chinese (TRANSLATE campaign message to Simplified Chinese)
- Korea: Korean (TRANSLATE campaign message to Korean)
- Italy: Italian (TRANSLATE campaign message to Italian)
- Brazil/Portugal: Portuguese (TRANSLATE campaign message to Portuguese)
- Russia: Russian (TRANSLATE campaign message to Russian)
- Middle East: Arabic (TRANSLATE campaign message to Arabic where appropriate)
- Other markets: Use the primary language of that market (TRANSLATE campaign message)

CULTURAL ADAPTATION EXAMPLES:
- Japan: Minimalist, zen aesthetics, soft colors, cherry blossoms, respect for negative space
- China: Red/gold colors for luck, prosperity themes, dynamic compositions
- Germany: Precision, quality, clean lines, technical excellence
- Middle East: Ornate patterns, rich colors, family values, luxury emphasis
- US: Bold, energetic, aspirational, diversity representation
- Scandinavia: Minimalist, natural materials, muted colors, hygge concepts

YOUR TASK:
Transform campaign briefs into detailed, optimized, and culturally adapted image generation prompts.

CRITICAL REQUIREMENTS:
1. Write in natural, coherent language (subject + action + environment)
2. ALL text elements MUST be in double quotes with appropriate language:
   - Campaign message: Keep in English for US/UK/Australia/Canada, TRANSLATE for other markets
     Examples: "Run Further" (US) → keep as "Run Further", (Germany) → "Laufe Weiter", (Japan) → "走り続ける"
   - Brand names: Keep in English unless culturally inappropriate
3. Include ALL products mentioned - show actual products in the scene naturally
4. If no brand name provided, generate one that fits products and target market
5. Describe brand logo placement prominently (typically top-left or top-right corner)
6. State this is for "advertising banner for [TARGET MARKET] market"
7. Adapt visual style, colors, composition to match target market cultural preferences
8. Be specific about lighting, colors, composition, and atmosphere
9. Create a cohesive, professional advertising scene that resonates with the local culture

Generate the following fields:
- image_prompt: The complete visual description
- translated_campaign_message: The campaign message in the target market language (exactly as it appears in your image_prompt)
- brand_mentions: Count of times the brand name appears in quotes
- includes_logo: true if you mention logo placement
- includes_campaign_message: true if you include the campaign message text"""

    # Build user prompt with campaign details
    products = campaign.get("products", [])
    target_market = campaign.get("target_market", "")
    target_audience = campaign.get("target_audience", "")
    campaign_message = campaign.get("campaign_message", "")
    brand_name = campaign.get("brand_name", "").strip()

    # Convert products to simple list of strings
    products_list = [str(p) for p in products]

    # Build brand-specific instructions
    if brand_name:
        brand_instruction = f"""Brand Name: "{brand_name}"
- The brand name "{brand_name}" MUST appear in double quotes multiple times in your prompt
- Include the "{brand_name}" logo prominently visible in the image (typically top-left or top-right corner)
- Ensure strong brand presence throughout the scene"""
    else:
        brand_instruction = """Brand Name: Not specified
- Generate an appropriate brand name for these products and target market
- The generated brand name MUST appear in double quotes multiple times in your prompt
- Include the logo with this brand name prominently visible in the image (typically top-left or top-right corner)"""

    # Add assets context if available
    assets_section = ""
    if assets_context:
        assets_section = f"""

ADDITIONAL CREATIVE GUIDANCE:
{assets_context}

These guidelines should inform the visual style, mood, and creative approach of the banner."""

    # Add reference image guidance if available
    reference_image_section = ""
    if has_reference_images:
        reference_image_section = """

REFERENCE IMAGES AVAILABLE:
Reference images have been provided as visual style guides. Use these reference images to:
- Match the overall aesthetic, color palette, and composition style
- Align with the visual mood and atmosphere shown in the references
- Incorporate similar lighting and artistic approach
- Maintain consistency with the reference style while showcasing the campaign products

The input reference images should guide the creative direction while ensuring all campaign requirements are met."""

    user_prompt = f"""Campaign Brief:
Products: {', '.join(products_list)}
Target Market: {target_market}
Target Audience: {target_audience}
Campaign Message (ORIGINAL ENGLISH): "{campaign_message}"
{brand_instruction}{assets_section}{reference_image_section}

Create a detailed Seedream 4.0 optimized prompt for a professional advertising banner that showcases ALL products together.

CRITICAL LOCALIZATION REQUIREMENTS FOR {target_market.upper()} MARKET:
1. Campaign Message Translation:
   - If {target_market} is US, UK, Australia, or Canada: Use the English message "{campaign_message}" AS-IS (do NOT translate)
   - For other markets: TRANSLATE "{campaign_message}" to the primary language of {target_market}
2. Adapt visual style, colors, and composition to {target_market} cultural preferences
3. Consider {target_market} cultural symbolism, color meanings, and aesthetic values
4. The campaign message MUST appear in the image in double quotes

SEEDREAM 4.0 PROMPT REQUIREMENTS:
1. Use natural, coherent language: describe subject + action + environment
2. Put ALL text in double quotes:
   - Brand name as "{brand_name if brand_name else '<Generated Brand>'}"
   - Campaign message: Use English AS-IS for US/UK/Australia/Canada, TRANSLATE to local language for other markets
3. Show all actual products in the scene: {', '.join(products_list)}
4. Specify this is for an "advertising banner for {target_market} market"
5. Include specific details about lighting, colors, composition, and atmosphere reflecting {target_market} aesthetic
6. Describe brand logo placement clearly (e.g., "top-right corner with clear visibility")
7. Use professional advertising photography aesthetics appropriate for {target_market}
8. Create a cohesive scene that naturally features all products together

IMPORTANT:
- For English-speaking markets (US, UK, Australia, Canada): Use "{campaign_message}" exactly as provided
- For other markets: Translate "{campaign_message}" to the target market's primary language

Target the visual style and cultural preferences for {target_market} market and {target_audience} audience."""

    logger.info("Optimizing prompt with GPT-4 (structured output)...")

    # Generate optimized prompt using GPT-4 with JSON mode (streaming approach)
    # Note: Replicate's OpenAI models return lists, so we use streaming directly
    full_response = ""
    for event in replicate.stream(
        "openai/gpt-4.1-nano",
        input={
            "prompt": user_prompt,
            "system_prompt": system_prompt,
            "temperature": 0.7,
            "max_completion_tokens": 600,
            "top_p": 1,
            "presence_penalty": 0,
            "frequency_penalty": 0,
            "response_format": {"type": "json_object"}
        },
    ):
        full_response += str(event)

    full_response = full_response.strip()

    # Try to parse as JSON
    try:
        # Clean up common JSON formatting issues
        cleaned_response = full_response
        # Fix trailing quotes in strings (e.g., "text"" -> "text")
        cleaned_response = re.sub(r'""([,\}])', r'"\1', cleaned_response)

        result = json.loads(cleaned_response)

        logger.info(f"Structured output validation:")
        logger.info(f"  Brand mentions: {result.get('brand_mentions', 'N/A')}")
        logger.info(f"  Includes logo: {result.get('includes_logo', 'N/A')}")
        logger.info(f"  Includes campaign message: {result.get('includes_campaign_message', 'N/A')}")
        logger.info(f"  Translated campaign message: {result.get('translated_campaign_message', 'N/A')}")

        optimized_prompt = result['image_prompt']
        translated_message = result.get('translated_campaign_message', campaign.get('campaign_message', ''))
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Could not parse JSON response: {e}. Using raw response.")
        optimized_prompt = full_response
        translated_message = campaign.get('campaign_message', '')

    return optimized_prompt, translated_message


def generate_brand_name(products: list, target_market: str, target_audience: str) -> str:
    """Generate a brand name using LLM if not provided

    Args:
        products: List of products
        target_market: Target market
        target_audience: Target audience

    Returns:
        Generated brand name
    """
    products_list = [str(p) for p in products]

    system_prompt = """You are an expert brand strategist. Generate a compelling, memorable brand name that fits the products and target market."""

    user_prompt = f"""Generate a brand name for the following products:
Products: {', '.join(products_list)}
Target Market: {target_market}
Target Audience: {target_audience}

Generate a single, compelling brand name (2-3 words maximum) that:
- Is memorable and brandable
- Fits the products and target market
- Is appropriate for the target audience
- Works well in the {target_market} market

Return ONLY the brand name, nothing else."""

    logger.info("Generating brand name with LLM...")

    full_response = ""
    for event in replicate.stream(
        "openai/gpt-4.1-nano",
        input={
            "prompt": user_prompt,
            "system_prompt": system_prompt,
            "temperature": 0.8,
            "max_completion_tokens": 50,
            "top_p": 1,
            "presence_penalty": 0,
            "frequency_penalty": 0,
        },
    ):
        full_response += str(event)

    brand_name = full_response.strip().strip('"').strip("'").strip()
    logger.info(f"Generated brand name: {brand_name}")
    return brand_name


def generate_campaign_message(products: list, target_market: str, target_audience: str, brand_name: str = "") -> str:
    """Generate a campaign message/slogan using LLM if not provided

    Args:
        products: List of products
        target_market: Target market
        target_audience: Target audience
        brand_name: Brand name (optional)

    Returns:
        Generated campaign message in English (will be translated later)
    """
    products_list = [str(p) for p in products]

    system_prompt = """You are an expert copywriter specializing in advertising slogans and campaign messages. Generate compelling, memorable campaign messages that resonate with target audiences."""

    brand_section = f"Brand Name: {brand_name}\n" if brand_name else ""

    user_prompt = f"""Generate a compelling campaign message/slogan for the following:
{brand_section}Products: {', '.join(products_list)}
Target Market: {target_market}
Target Audience: {target_audience}

Generate a single, compelling campaign message/slogan (3-6 words) that:
- Is memorable and impactful
- Highlights key benefits or emotional appeal
- Resonates with the target audience
- Works well for advertising banners
- Is in English (it will be translated to {target_market} language later if needed)
- CRITICAL: DO NOT include the brand name "{brand_name}" in the campaign message (the brand name will appear separately)

Return ONLY the campaign message, nothing else."""

    logger.info("Generating campaign message with LLM...")

    full_response = ""
    for event in replicate.stream(
        "openai/gpt-4.1-nano",
        input={
            "prompt": user_prompt,
            "system_prompt": system_prompt,
            "temperature": 0.8,
            "max_completion_tokens": 50,
            "top_p": 1,
            "presence_penalty": 0,
            "frequency_penalty": 0,
        },
    ):
        full_response += str(event)

    campaign_message = full_response.strip().strip('"').strip("'").strip()
    logger.info(f"Generated campaign message: {campaign_message}")
    return campaign_message


def validate_campaign(campaign):
    """Validate campaign brief has all required fields"""
    required_fields = ["products", "target_market", "target_audience"]

    for field in required_fields:
        if field not in campaign:
            raise ValueError(f"Missing required field: {field}")

    # Validate at least 2 products
    products = campaign.get("products", [])
    if len(products) < 2:
        raise ValueError(f"Campaign must have at least 2 products (found {len(products)})")

    logger.info("✓ Campaign brief validation passed")
