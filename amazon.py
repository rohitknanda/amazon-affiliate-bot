"""
amazon.py
=========
Fetches Amazon products with your affiliate tag.

TWO MODES (chosen automatically based on what credentials are set):

  MODE 1: PA-API (Amazon Product Advertising API) — REAL product data
  ------------------------------------------------------------------
  Requires Amazon Associates approval (need 3 qualifying sales first).
  Gives you real-time product titles, prices, ratings, images.
  Set AMAZON_ACCESS_KEY + AMAZON_SECRET_KEY + AMAZON_PARTNER_TAG in .env.

  MODE 2: Search URL Fallback — WORKS IMMEDIATELY, no PA-API needed
  ------------------------------------------------------------------
  Generates Amazon search URLs with your affiliate tag baked in.
  User clicks → lands on Amazon search results → any purchase = your commission.
  This is the recommended mode when starting out.
"""
import logging
from urllib.parse import quote_plus
from config import settings

log = logging.getLogger(__name__)

# Try to import PA-API library (only if user installs it)
try:
    from amazon_paapi import AmazonApi
    PAAPI_AVAILABLE = True
except ImportError:
    PAAPI_AVAILABLE = False


def search_amazon_products(
    keywords: str,
    max_price: int | None = None,
    min_rating: float = 4.0,
    limit: int = 3,
) -> list[dict]:
    """
    Search Amazon and return up to `limit` products.
    Returns list of dicts with keys: asin, title, price, rating, review_count,
    image_url, affiliate_url, highlight.
    """
    # Decide which mode to use
    if (
        PAAPI_AVAILABLE
        and settings.amazon_access_key
        and settings.amazon_secret_key
    ):
        log.info("Using PA-API mode")
        return _search_via_paapi(keywords, max_price, min_rating, limit)
    else:
        log.info("Using Search URL fallback mode (no PA-API)")
        return _search_via_fallback(keywords, max_price, min_rating, limit)


# ---------- MODE 1: PA-API (real product data) ----------

def _search_via_paapi(
    keywords: str, max_price: int | None, min_rating: float, limit: int
) -> list[dict]:
    """
    Use Amazon's official Product Advertising API.
    Returns real-time product data.
    """
    try:
        amazon = AmazonApi(
            settings.amazon_access_key,
            settings.amazon_secret_key,
            settings.amazon_affiliate_tag,
            country=settings.amazon_country,  # "IN" for amazon.in
        )

        # PA-API search
        search_result = amazon.search_items(
            keywords=keywords,
            item_count=limit,
            min_reviews_rating=int(min_rating),
            max_price=max_price * 100 if max_price else None,  # price in paise
        )

        products = []
        for item in search_result.items[:limit]:
            # Extract fields safely
            asin = item.asin
            title = item.item_info.title.display_value
            price = None
            if item.offers and item.offers.listings:
                price_obj = item.offers.listings[0].price
                if price_obj:
                    price = int(price_obj.amount)
            rating = None
            review_count = "N/A"
            if hasattr(item, "customer_reviews") and item.customer_reviews:
                rating = item.customer_reviews.star_rating
                review_count = item.customer_reviews.count
            image_url = item.images.primary.large.url if item.images else None

            # Build affiliate URL (PA-API responses already include partner tag)
            affiliate_url = item.detail_page_url

            products.append({
                "asin": asin,
                "title": title,
                "price": price,
                "rating": rating,
                "review_count": review_count,
                "image_url": image_url,
                "affiliate_url": affiliate_url,
                "highlight": "Top rated by Amazon customers",
            })
        return products

    except Exception as e:
        log.exception("PA-API call failed, falling back to search URL")
        return _search_via_fallback(keywords, max_price, min_rating, limit)


# ---------- MODE 2: Search URL fallback (works with no extra setup) ----------

def _search_via_fallback(
    keywords: str, max_price: int | None, min_rating: float, limit: int
) -> list[dict]:
    """
    Generate Amazon search URLs with affiliate tag.
    Doesn't need PA-API approval. Works immediately.

    Strategy: We create 3 *curated* searches with different angles so the user
    gets variety. Each links to filtered Amazon search results with your tag.
    """
    domain = _amazon_domain(settings.amazon_country)
    tag = settings.amazon_affiliate_tag

    # Build search variants for variety
    variants = [
        {
            "label": "Best Sellers",
            "suffix": "",
            "sort": "exact-aware-popularity-rank",
            "highlight": "Most popular pick — bestseller in this category",
        },
        {
            "label": "Highly Rated",
            "suffix": "",
            "sort": "review-rank",
            "highlight": "Top-rated by thousands of customers",
        },
        {
            "label": "Best Value",
            "suffix": "",
            "sort": "price-asc-rank",
            "highlight": "Best price-to-quality ratio in this range",
        },
    ]

    products = []
    for i, v in enumerate(variants[:limit]):
        # Build the Amazon search URL with affiliate tag
        url_params = {
            "k": keywords + (" " + v["suffix"] if v["suffix"] else ""),
            "s": v["sort"],
            "tag": tag,
        }
        if max_price:
            url_params["rh"] = f"p_36:0-{max_price * 100}"  # price in paise

        # Construct URL
        query_str = "&".join(f"{k}={quote_plus(str(v))}" for k, v in url_params.items())
        url = f"https://www.{domain}/s?{query_str}"

        # Build human-readable title
        price_part = f" (under ₹{max_price})" if max_price else ""
        title = f"{v['label']}: {keywords.title()}{price_part}"

        products.append({
            "asin": f"search-{i}",  # not a real ASIN since this is a search link
            "title": title,
            "price": None,            # we don't know the exact price in fallback mode
            "rating": None,
            "review_count": "many",
            "image_url": None,
            "affiliate_url": url,
            "highlight": v["highlight"],
        })

    return products


def _amazon_domain(country_code: str) -> str:
    """Map country code → Amazon domain."""
    return {
        "IN": "amazon.in",
        "US": "amazon.com",
        "UK": "amazon.co.uk",
        "DE": "amazon.de",
        "CA": "amazon.ca",
        "AU": "amazon.com.au",
        "JP": "amazon.co.jp",
    }.get(country_code.upper(), "amazon.com")
