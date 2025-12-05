"""
Slug generation utilities for SEO-friendly URLs
"""
import re
from typing import Optional


def generate_property_slug(
    listing_type: str,
    beds: int,
    property_type: str,
    lga: str,
    state: str,
    property_id: str,
    title: Optional[str] = None
) -> str:
    """
    Generate SEO-friendly slug for property URLs
    
    Format: /for-{listing_type}/{beds}-bedroom-{type}-{lga}-{state}-{id}
    Example: /for-rent/3-bedroom-flat-lekki-lagos-690d2078c21cb96f97d3a21c
    
    Args:
        listing_type: 'rent' or 'sale'
        beds: Number of bedrooms
        property_type: Type of property (flat, house, duplex, etc.)
        lga: Local Government Area (e.g., Lekki, Ikeja)
        state: State name (e.g., Lagos, Abuja)
        property_id: MongoDB ObjectId string
        title: Optional property title for more context
        
    Returns:
        SEO-friendly slug string
    """
    
    def slugify(text: str) -> str:
        """Convert text to URL-safe slug"""
        # Convert to lowercase
        text = text.lower()
        # Remove special characters, keep alphanumeric and spaces
        text = re.sub(r'[^a-z0-9\s-]', '', text)
        # Replace spaces with hyphens
        text = re.sub(r'\s+', '-', text)
        # Remove multiple consecutive hyphens
        text = re.sub(r'-+', '-', text)
        # Strip hyphens from start and end
        text = text.strip('-')
        return text
    
    # Slugify components
    listing_slug = slugify(listing_type)
    type_slug = slugify(property_type)
    lga_slug = slugify(lga)
    state_slug = slugify(state)
    
    # Build slug parts
    parts = []
    
    # Add bedroom count
    if beds > 0:
        bedroom_text = f"{beds}-bedroom" if beds > 1 else "1-bedroom"
        parts.append(bedroom_text)
    
    # Add property type
    if type_slug:
        parts.append(type_slug)
    
    # Add location (LGA)
    if lga_slug:
        parts.append(lga_slug)
    
    # Add state
    if state_slug:
        parts.append(state_slug)
    
    # Add property ID (last 8 characters for brevity)
    parts.append(property_id[-8:] if len(property_id) > 8 else property_id)
    
    # Combine parts
    slug_path = '-'.join(parts)
    
    # Add listing type prefix
    full_slug = f"for-{listing_slug}/{slug_path}"
    
    return full_slug


def generate_slug_from_title(
    title: str,
    property_id: str,
    max_length: int = 100
) -> str:
    """
    Generate slug primarily from property title
    
    Format: {slugified-title}-{id}
    Example: luxury-3-bedroom-flat-with-bq-in-lekki-phase-1-690d2078
    
    Args:
        title: Property title
        property_id: MongoDB ObjectId string
        max_length: Maximum slug length
        
    Returns:
        SEO-friendly slug
    """
    def slugify(text: str) -> str:
        """Convert text to URL-safe slug"""
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s-]', '', text)
        text = re.sub(r'\s+', '-', text)
        text = re.sub(r'-+', '-', text)
        text = text.strip('-')
        return text
    
    # Slugify title
    title_slug = slugify(title)
    
    # Add shortened ID
    short_id = property_id[-8:] if len(property_id) > 8 else property_id
    
    # Combine
    slug = f"{title_slug}-{short_id}"
    
    # Truncate if too long (keep the ID intact)
    if len(slug) > max_length:
        title_part = title_slug[:max_length - len(short_id) - 1]
        slug = f"{title_part}-{short_id}"
    
    return slug


def extract_id_from_slug(slug: str) -> Optional[str]:
    """
    Extract property ID from slug
    
    Assumes ID is the last segment after the final hyphen
    
    Args:
        slug: Property slug URL
        
    Returns:
        Extracted ID or None
    """
    # Remove leading/trailing slashes
    slug = slug.strip('/')
    
    # Get the last part after splitting by '/'
    if '/' in slug:
        slug = slug.split('/')[-1]
    
    # Get the last part after splitting by '-'
    parts = slug.split('-')
    if parts:
        return parts[-1]
    
    return None


def get_full_property_url(slug: str, base_url: str = "https://houzdey.com") -> str:
    """
    Generate full property URL from slug
    
    Args:
        slug: Property slug (with or without leading slash)
        base_url: Base domain URL
        
    Returns:
        Complete property URL
    """
    # Ensure slug starts with /
    if not slug.startswith('/'):
        slug = f'/{slug}'
    
    # Remove trailing slash from base_url
    base_url = base_url.rstrip('/')
    
    return f"{base_url}/properties/{slug}"
