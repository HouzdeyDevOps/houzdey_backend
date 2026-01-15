// N8N-Compatible Property Parser for Nigeria Property Centre
// Returns data in format: [{ json: {...} }]

// Get input data from n8n
const html = $input.first().json.data;
const meta = $('Loop Over Properties').first().json;

// Helper functions
function stripHtml(text) {
  return text ? text.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim() : '';
}

function extractNumber(text) {
  if (!text) return null;
  const match = text.match(/[\d,]+/);
  return match ? parseInt(match[0].replace(/,/g, '')) : null;
}

// 1. TITLE
let title = '';
const titleMatch = html.match(/<h1[^>]*class="[^"]*page-title[^"]*"[^>]*>([^<]+)<\/h1>/i);
if (titleMatch) {
  title = stripHtml(titleMatch[1]);
}

// 2. PROPERTY TYPE
let propertyType = 'flat';
const typeMatch = html.match(/(\d+)\s+bedroom\s+(flat|apartment|house|duplex|bungalow|detached|semi-detached|terrace|studio|penthouse)/i);
if (typeMatch) {
  const rawType = typeMatch[2].toLowerCase();
  if (rawType === 'flat' || rawType === 'apartment') propertyType = 'flat';
  else if (['house', 'duplex', 'bungalow', 'detached', 'semi-detached', 'terrace'].includes(rawType)) propertyType = 'house';
  else if (rawType === 'studio') propertyType = 'studio';
  else if (rawType === 'penthouse') propertyType = 'penthouse';
}

// 3. PRICE
let price = 0;
let priceFrequency = 'per annum';
const priceMatch = html.match(/<span[^>]*itemprop="price"[^>]*content="([^"]+)"[^>]*>([^<]+)<\/span><span[^>]*class="period"[^>]*>([^<]+)<\/span>/i);
if (priceMatch) {
  price = parseFloat(priceMatch[1].replace(/,/g, ''));
  priceFrequency = priceMatch[3].trim();
} else {
  const altPriceMatch = html.match(/₦\s*<\/span><span[^>]*>([0-9,]+)<\/span>/i);
  if (altPriceMatch) {
    price = parseFloat(altPriceMatch[1].replace(/,/g, ''));
  }
}

// Determine listing type and prices
const listingType = meta.listingType || 'for-rent';
let rentalPrice = 0;
let salePrice = 0;

if (listingType.includes('rent') || listingType.includes('let')) {
  rentalPrice = price;
} else if (listingType.includes('sale')) {
  salePrice = price;
}

// 4. BEDROOMS
let beds = 0;
const bedsMatch = html.match(/<span[^>]*itemprop="value"[^>]*>(\d+)<\/span>\s*<span[^>]*itemprop="name"[^>]*>Bedrooms<\/span>/i);
if (bedsMatch) {
  beds = parseInt(bedsMatch[1]);
}

// 5. BATHROOMS
let baths = 0;
const bathsMatch = html.match(/<span[^>]*itemprop="value"[^>]*>(\d+)<\/span>\s*<span[^>]*itemprop="name"[^>]*>Bathrooms<\/span>/i);
if (bathsMatch) {
  baths = parseInt(bathsMatch[1]);
}

// 6. TOILETS
let toilets = 0;
const toiletsMatch = html.match(/<span[^>]*itemprop="value"[^>]*>(\d+)<\/span>\s*<span[^>]*itemprop="name"[^>]*>Toilets<\/span>/i);
if (toiletsMatch) {
  toilets = parseInt(toiletsMatch[1]);
} else {
  toilets = baths;
}

// 7. PARKING
let parkingSpaces = 0;
const parkingMatch = html.match(/<span[^>]*itemprop="value"[^>]*>(\d+)<\/span>\s*<span[^>]*itemprop="name"[^>]*>Parking Spaces<\/span>/i);
if (parkingMatch) {
  parkingSpaces = parseInt(parkingMatch[1]);
}

// 8. DESCRIPTION
let description = '';
const descMatch = html.match(/<p[^>]*itemprop="description"[^>]*>([\s\S]*?)<\/p>/i);
if (descMatch) {
  description = stripHtml(descMatch[1])
    .replace(/\s*<br\s*\/?>\s*/gi, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

if (!description && title) {
  description = title;
}

// 9. AMENITIES
const amenities = [];
const amenityKeywords = [
  'en-suite', 'ensuite', 'all rooms en-suite',
  'swimming pool', 'pool',
  'gym', 'gymnasium', 'fitness center',
  'parking', 'garage', 'car park',
  'security', '24/7 security', 'cctv', 'security guard',
  'generator', 'standby generator',
  'water heater', 'heater',
  'air conditioning', 'ac', 'a/c',
  'furnished', 'fully furnished',
  'serviced',
  'balcony', 'terrace', 'garden',
  'wifi', 'internet',
  'cable tv', 'dstv',
  'fitted kitchen', 'modern kitchen',
  'wardrobe', 'closet',
  'elevator', 'lift',
  'borehole',
  'inverter', 'solar',
  'stamped concrete', 'quality tiles',
  'pop ceiling',
  'walk-in shower', 'shower',
  'chandeliers', 'spot lights', 'automated lights'
];

const descriptionLower = description.toLowerCase();
const seenAmenities = new Set();

for (const amenity of amenityKeywords) {
  if (descriptionLower.includes(amenity.toLowerCase())) {
    const normalized = amenity
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
    
    if (!seenAmenities.has(normalized.toLowerCase())) {
      amenities.push({ name: normalized });
      seenAmenities.add(normalized.toLowerCase());
    }
  }
}

// 10. CONDITION
let condition = 'fairly-used';
if (descriptionLower.includes('newly built') || descriptionLower.includes('new build') || 
    descriptionLower.includes('brand new')) {
  condition = 'newly-built';
} else if (descriptionLower.includes('renovated') || descriptionLower.includes('refurbished')) {
  condition = 'renovated';
}

// 11. FURNISHING
let furnishing = 'unfurnished';
if (descriptionLower.includes('fully furnished')) {
  furnishing = 'furnished';
} else if (descriptionLower.includes('semi furnished') || descriptionLower.includes('semi-furnished')) {
  furnishing = 'semi-furnished';
} else if (descriptionLower.includes('furnished')) {
  furnishing = 'furnished';
}

// 12. ADDRESS
let address = '';
const addressMatch = html.match(/<address[^>]*>[\s\S]*?<i[^>]*><\/i>\s*&nbsp;([^<]+)<\/address>/i);
if (addressMatch) {
  address = stripHtml(addressMatch[1]);
}

// 13. STATE
let state = 'Lagos';
if (meta.state) {
  state = meta.state.charAt(0).toUpperCase() + meta.state.slice(1);
}

// 14. LGA
let lga = '';
const lgaMatch = address.match(/([^,]+),\s*(?:Lagos|Abuja)/i);
if (lgaMatch) {
  lga = lgaMatch[1].trim();
} else if (meta.detailUrl) {
  const urlLgaMatch = meta.detailUrl.match(/\/(?:lagos|abuja)\/([^\/]+)\//i);
  if (urlLgaMatch) {
    lga = urlLgaMatch[1]
      .replace(/-/g, ' ')
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }
}

// 15. ESTATE
let estate = '';
const estateMatch = address.match(/^([^,]+)/);
if (estateMatch) {
  const potentialEstate = estateMatch[1].trim();
  if (potentialEstate.toLowerCase().includes('estate') || 
      potentialEstate.toLowerCase().includes('gra') ||
      potentialEstate.toLowerCase().includes('court') ||
      potentialEstate.toLowerCase().includes('gardens')) {
    estate = potentialEstate;
  }
}

// 16. SIZE
let size = '';
const sizeMatch = html.match(/<strong>Size:<\/strong>\s*([^<]+)/i);
if (sizeMatch) {
  size = stripHtml(sizeMatch[1]);
}

// 17. IMAGES
const images = [];
const imageRegex = /https:\/\/images\.nigeriapropertycentre\.com\/properties\/images\/\d+\/[a-f0-9]+-[^"'\s]+\.jpeg/gi;
let imgMatch;

while ((imgMatch = imageRegex.exec(html)) !== null) {
  const imgUrl = imgMatch[0];
  if (!images.includes(imgUrl) && !imgUrl.includes('/thumbs/')) {
    images.push(imgUrl);
  }
}

// 18. FEES
let agencyFee = 0;
const agencyFeeMatch = html.match(/agency\s+fee[:\s]*₦?\s*([0-9,]+)/i);
if (agencyFeeMatch) {
  agencyFee = parseFloat(agencyFeeMatch[1].replace(/,/g, ''));
}

let legalFee = 0;
const legalFeeMatch = html.match(/legal\s+fee[:\s]*₦?\s*([0-9,]+)/i);
if (legalFeeMatch) {
  legalFee = parseFloat(legalFeeMatch[1].replace(/,/g, ''));
}

// 19. PROPERTY REF
let propertyRef = '';
const refMatch = html.match(/<strong>Property Ref:<\/strong>\s*(\d+)/i);
if (refMatch) {
  propertyRef = refMatch[1];
}

// 20. AGENT INFO
let agentName = '';
let agentPhone = '';

const agentNameMatch = html.match(/<a href="\/agents\/[^"]+"><strong>([^<]+)<\/strong><\/a>/i);
if (agentNameMatch) {
  agentName = stripHtml(agentNameMatch[1]);
}

const phoneMatch = html.match(/id="fullPhoneNumbers"[^>]*value="([^"]+)"/i);
if (phoneMatch) {
  agentPhone = phoneMatch[1];
}

// Build property object
const property = {
  title: title || `${beds} Bedroom ${propertyType.charAt(0).toUpperCase() + propertyType.slice(1)} in ${lga || state}`,
  type: propertyType,
  price: price,
  rental_price: rentalPrice,
  sale_price: salePrice,
  listing_type: listingType.replace('for-', ''),
  
  beds: beds,
  baths: baths,
  toilets: toilets,
  parking_spaces: parkingSpaces,
  size: size,
  
  description: description,
  amenities: JSON.stringify(amenities),
  
  condition: condition,
  furnishing: furnishing,
  
  address: address,
  state: state,
  lga: lga,
  ward: '',
  estate: estate,
  
  images: images.slice(0, 15),
  
  agency_fee: agencyFee,
  legal_fee: legalFee,
  
  status: 'available',
  property_ref: propertyRef,
  
  agent_name: agentName,
  agent_phone: agentPhone,
  
  source: 'nigeriapropertycentre',
  source_url: meta.detailUrl,
  source_id: propertyRef || meta.propertyId,
  
  // Metadata for next steps
  _apiBaseUrl: meta.apiBaseUrl,
  _ownerId: meta.ownerId
};

// Validation
if (!property.title || !property.price || property.price === 0) {
  return [{ json: { skip: true, reason: 'Missing required fields', propertyId: meta.propertyId } }];
}

// IMPORTANT: Return in n8n format
return [{ json: property }];