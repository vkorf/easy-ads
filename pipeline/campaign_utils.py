"""
Campaign utility functions for brand name generation, campaign message generation,
prompt optimization, and validation.

These functions are shared between the CLI (main.py) and the FastAPI backend.
"""

import logging
import json
import re
import os
from typing import Tuple, List, Set, Dict
from pydantic import BaseModel, Field
from openai import OpenAI

logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_TOKEN"))


# LEGAL COMPLIANCE - Prohibited Words List
# These words are flagged as potentially problematic in advertising content
PROHIBITED_WORDS: Set[str] = {
    # False/misleading claims
    "guaranteed", "miracle", "cure", "100%", "risk-free", "free money",
    "get rich quick", "instant wealth", "overnight success",

    # Offensive/inappropriate
    "kill", "death", "suicide", "violence", "weapon", "drug", "cocaine",
    "heroin", "marijuana", "cannabis", "tobacco", "cigarette", "alcohol",
    "beer", "wine", "vodka", "whiskey",

    # Discriminatory terms
    "race", "racist", "discrimination", "hate", "supremacy",

    # Health claims (without approval)
    "cure cancer", "cure diabetes", "lose weight instantly", "miracle pill",
    "FDA approved" , "clinically proven", "doctor recommended",

    # Financial scams
    "pyramid scheme", "ponzi", "mlm", "multi-level marketing",
    "work from home guaranteed", "easy money", "no effort required",

    # Sexual/adult content
    "porn", "pornography", "xxx", "adult content", "sex",

    # Gambling (in restricted markets)
    "casino", "betting", "gamble", "lottery", "slot machine",

    # Weapons/dangerous items
    "gun", "rifle", "firearm", "explosive", "bomb", "ammunition"
}


class LegalComplianceError(Exception):
    """Raised when content contains prohibited words or violates legal guidelines"""

    def __init__(self, message: str, prohibited_words_found: List[str]):
        self.prohibited_words_found = prohibited_words_found
        super().__init__(message)


def check_legal_compliance(campaign: dict) -> Dict[str, any]:
    """
    Check campaign content for prohibited words and legal compliance issues.

    This function scans all user-provided content in the campaign brief
    (products, campaign message, brand name, target audience) for prohibited
    words that may violate advertising standards or legal requirements.

    Args:
        campaign: Campaign brief dictionary with user input

    Returns:
        Dictionary with compliance results:
        - is_compliant: bool
        - prohibited_words_found: List[str] of flagged words
        - violations: Dict mapping field names to lists of prohibited words found

    Raises:
        LegalComplianceError: If prohibited words are found in the initial campaign form
    """
    violations: Dict[str, List[str]] = {}
    all_prohibited_found: Set[str] = set()

    # Fields to check
    fields_to_check = {
        "brand_name": campaign.get("brand_name", ""),
        "campaign_message": campaign.get("campaign_message", ""),
        "target_audience": campaign.get("target_audience", ""),
        "products": " ".join([str(p) for p in campaign.get("products", [])])
    }

    logger.info("Running legal compliance check on campaign content...")

    for field_name, content in fields_to_check.items():
        if not content:
            continue

        # Convert to lowercase for case-insensitive matching
        content_lower = content.lower()

        # Check for prohibited words
        found_words = []
        for prohibited_word in PROHIBITED_WORDS:
            # Use word boundary matching to avoid false positives
            # e.g., "guaranteed" won't match "guard"
            pattern = r'\b' + re.escape(prohibited_word.lower()) + r'\b'
            if re.search(pattern, content_lower):
                found_words.append(prohibited_word)
                all_prohibited_found.add(prohibited_word)

        if found_words:
            violations[field_name] = found_words
            logger.warning(f"⚠ Legal compliance issue in '{field_name}': {', '.join(found_words)}")

    # Determine compliance status
    is_compliant = len(all_prohibited_found) == 0

    result = {
        "is_compliant": is_compliant,
        "prohibited_words_found": sorted(list(all_prohibited_found)),
        "violations": violations
    }

    if not is_compliant:
        # Log detailed violation report
        logger.error("="*60)
        logger.error("LEGAL COMPLIANCE CHECK FAILED")
        logger.error("="*60)
        logger.error(f"Found {len(all_prohibited_found)} prohibited word(s) in campaign content:")
        for field, words in violations.items():
            logger.error(f"  {field}: {', '.join(words)}")
        logger.error("="*60)

        # Raise error to stop pipeline
        error_msg = (
            f"Campaign content contains prohibited words: {', '.join(sorted(all_prohibited_found))}. "
            f"Please revise your campaign brief to remove these terms. "
            f"Violations found in: {', '.join(violations.keys())}"
        )
        raise LegalComplianceError(error_msg, sorted(list(all_prohibited_found)))

    logger.info("✓ Legal compliance check passed - no prohibited words found")
    return result


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

    Raises:
        LegalComplianceError: If campaign content contains prohibited words
    """

    # STEP 1: Legal Compliance Check - Run BEFORE GPT processing
    # This validates the initial user input for prohibited content
    check_legal_compliance(campaign)

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
- BRAND NAMES: ALWAYS keep in English (NEVER translate brand names)
- CAMPAIGN MESSAGES/SLOGANS: Translate to the target market's primary language
- Adapt visual styles, colors, and aesthetics to match cultural preferences
- Consider cultural symbolism, color meanings, and design preferences
- Adjust composition and imagery to resonate with local audiences

LANGUAGE TRANSLATION RULES FOR CAMPAIGN MESSAGES ONLY:
- US/UK/Australia/Canada: English (keep original English campaign message)
- Germany/Austria/Switzerland: German (translate campaign message to German)
- France: French (translate campaign message to French)
- Spain/Mexico/Latin America: Spanish (translate campaign message to Spanish)
- Japan: Japanese (translate campaign message to Japanese)
- China: Simplified Chinese (translate campaign message to Simplified Chinese)
- Korea: Korean (translate campaign message to Korean)
- Italy: Italian (translate campaign message to Italian)
- Brazil/Portugal: Portuguese (translate campaign message to Portuguese)
- Russia: Russian (translate campaign message to Russian)
- Middle East: Arabic (translate campaign message to Arabic where appropriate)
- Other markets: Use the primary language of that market (translate campaign message)

CRITICAL: Brand names must ALWAYS remain in English regardless of target market!

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
2. Include visible text in the image using this format: text in quotation marks
   - Brand name: ALWAYS in English (NEVER translate), appears as: the BRANDNAME brand
   - Campaign message: Translated to local language, appears as: localized message text
   - Example for Germany: the banner shows Nike (English brand name) with text "Laufe Weiter" (German slogan)
3. Include ALL products mentioned - show actual products in the scene naturally
4. If no brand name provided, generate one in English that fits the products
5. Describe brand logo placement prominently (typically top-left or top-right corner)
6. State this is for an advertising banner for [TARGET MARKET] market
7. Adapt visual style, colors, composition to match target market cultural preferences
8. Be specific about lighting, colors, composition, and atmosphere
9. Create a cohesive, professional advertising scene that resonates with the local culture
10. IMPORTANT: Keep the entire image description as one continuous paragraph in the image_prompt field

Generate the following fields in JSON format:
- image_prompt: The complete visual description
- translated_campaign_message: The campaign message in the target market language (exactly as it appears in your image_prompt)
- brand_mentions: Count of times the brand name appears in quotes
- includes_logo: true if you mention logo placement
- includes_campaign_message: true if you include the campaign message text

Return your response as a JSON object."""

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
        brand_instruction = f"""Brand Name: {brand_name}
- The brand name {brand_name} must be visible as text in the image
- Include the {brand_name} logo prominently in top-left or top-right corner
- Describe the brand name appearing in the scene"""
    else:
        brand_instruction = """Brand Name: Not specified
- Generate an appropriate brand name for these products and target market
- The brand name must be visible as text in the image
- Include the logo prominently in top-left or top-right corner"""

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
Campaign Message: {campaign_message}
{brand_instruction}{assets_section}{reference_image_section}

Create a detailed image generation prompt for a professional advertising banner.

REQUIREMENTS:
1. Write one continuous paragraph describing the scene
2. Show all products ({', '.join(products_list)}) together in a natural setting
3. Brand name: ALWAYS keep "{brand_name if brand_name else '(generate one)'}" in ENGLISH - describe it appearing as visible text in the image
4. Campaign message: Translate "{campaign_message}" to local language - describe it appearing as visible text in the image
5. Include brand logo placement (top-left or top-right corner)
6. Specify this is an advertising banner for {target_market} market
7. Include lighting, colors, composition details for {target_market} aesthetic

CRITICAL LOCALIZATION RULES FOR {target_market}:
- BRAND NAME: Keep "{brand_name if brand_name else '(generate one)'}" in English (DO NOT TRANSLATE)
- CAMPAIGN MESSAGE: {"Keep in English" if target_market in ['US', 'UK', 'Australia', 'Canada'] else f"TRANSLATE to {target_market} language"}

Example for Germany: Brand "Nike" (English) with slogan "Laufe Weiter" (German translation of "Run Further")

The image_prompt field should be one complete paragraph with the brand name in English and campaign message in the local language."""

    logger.info("Optimizing prompt with GPT-4 (structured output)...")

    # Generate optimized prompt using GPT-4o-mini with JSON mode (gpt-4.1-nano struggles with quoted text in JSON)
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=600,
        top_p=1,
        presence_penalty=0,
        frequency_penalty=0,
        response_format={"type": "json_object"}
    )

    full_response = response.choices[0].message.content.strip()

    # Try to parse as JSON
    try:
        # Debug: Log first 800 chars of response to see any issues
        logger.debug(f"Raw response (first 800 chars): {full_response[:800]}")

        # Clean up common JSON formatting issues
        cleaned_response = full_response

        # Fix trailing quotes in strings (e.g., "text"" -> "text")
        cleaned_response = re.sub(r'""([,\}])', r'"\1', cleaned_response)

        # Remove any tab characters that might have been incorrectly inserted
        cleaned_response = cleaned_response.replace('\t', ' ')

        # Try to extract just the JSON object if there's extra text
        json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
        if json_match:
            cleaned_response = json_match.group(0)

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

    system_prompt = """You are an expert brand strategist. Generate compelling, memorable brand names in ENGLISH ONLY for global brands."""

    user_prompt = f"""Generate an English brand name for the following products:
Products: {', '.join(products_list)}
Target Market: {target_market}
Target Audience: {target_audience}

Generate a single, compelling brand name (2-3 words maximum) that:
- Is memorable and brandable
- MUST be in ENGLISH (use Latin alphabet only)
- Fits the products and target market culturally
- Is appropriate for the target audience
- Works well globally and in the {target_market} market

CRITICAL: The brand name MUST be in English, even if the target market is {target_market}.
International brands use English names for global recognition.

Return ONLY the English brand name, nothing else."""

    logger.info("Generating brand name with LLM...")

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.8,
        max_tokens=50,
        top_p=1,
        presence_penalty=0,
        frequency_penalty=0
    )

    brand_name = response.choices[0].message.content.strip().strip('"').strip("'").strip()
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

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.8,
        max_tokens=50,
        top_p=1,
        presence_penalty=0,
        frequency_penalty=0
    )

    campaign_message = response.choices[0].message.content.strip().strip('"').strip("'").strip()
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
