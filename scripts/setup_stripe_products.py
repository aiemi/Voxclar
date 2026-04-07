#!/usr/bin/env python3
"""Create Stripe products and prices for Voxclar, then print the price IDs to paste into .env."""
import stripe
import os

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
if not stripe.api_key:
    raise RuntimeError("Set STRIPE_SECRET_KEY env variable before running this script.")

def create_products():
    # ── Standard Plan: $19.99/mo, 300 min ──
    standard = stripe.Product.create(
        name="Voxclar Standard",
        description="300 min/month — Deepgram Nova-2 ASR, Claude-powered answers, cloud sync",
    )
    standard_price = stripe.Price.create(
        product=standard.id,
        unit_amount=1999,  # $19.99
        currency="usd",
        recurring={"interval": "month"},
    )
    print(f"STRIPE_STANDARD_PRICE_ID={standard_price.id}")

    # ── Pro Plan: $49.99/mo, 1000 min ──
    pro = stripe.Product.create(
        name="Voxclar Pro",
        description="1000 min/month — All AI models, priority support, cloud sync",
    )
    pro_price = stripe.Price.create(
        product=pro.id,
        unit_amount=4999,  # $49.99
        currency="usd",
        recurring={"interval": "month"},
    )
    print(f"STRIPE_PRO_PRICE_ID={pro_price.id}")

    # ── Lifetime: $299 one-time ──
    lifetime = stripe.Product.create(
        name="Voxclar Lifetime",
        description="One-time purchase — Local ASR, bring your own AI keys, device-locked",
    )
    lifetime_price = stripe.Price.create(
        product=lifetime.id,
        unit_amount=29900,  # $299
        currency="usd",
    )
    print(f"STRIPE_LIFETIME_PRICE_ID={lifetime_price.id}")

    # ── Time Boost: $9.99 one-time ──
    topup = stripe.Product.create(
        name="Voxclar Time Boost",
        description="+120 minutes (never expires)",
    )
    topup_price = stripe.Price.create(
        product=topup.id,
        unit_amount=999,  # $9.99
        currency="usd",
    )
    print(f"STRIPE_TOPUP_PRICE_ID={topup_price.id}")

    print("\n✅ Done! Copy the lines above into your .env file.")


if __name__ == "__main__":
    create_products()
