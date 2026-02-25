"""
Setup Stripe products and prices for TuExpertoFiscal

Run: python -m scripts.setup.setup_stripe

Creates:
- Product: TuExpertoFiscal Basic (€2.99/month, €29.99/year)
- Product: TuExpertoFiscal Pro (€9.99/month, €99.99/year)
- Updates .env with price IDs
"""

import os
import sys
import stripe
from dotenv import load_dotenv

load_dotenv()


def setup_stripe():
    stripe_key = os.getenv('STRIPE_SECRET_KEY', '')

    if not stripe_key or stripe_key.startswith('sk_test_your'):
        print("ERROR: Set STRIPE_SECRET_KEY in .env first!")
        print("Get it from: https://dashboard.stripe.com/apikeys")
        sys.exit(1)

    stripe.api_key = stripe_key
    print(f"Using Stripe key: {stripe_key[:12]}...")

    # Check if products already exist
    existing = stripe.Product.list(limit=10)
    for p in existing.data:
        if 'TuExpertoFiscal' in p.name:
            print(f"Found existing product: {p.name} ({p.id})")
            # List prices
            prices = stripe.Price.list(product=p.id, limit=10)
            for pr in prices.data:
                interval = pr.recurring.interval if pr.recurring else 'one-time'
                print(f"  Price: €{pr.unit_amount/100:.2f}/{interval} ({pr.id})")
            print()

    # Create Basic product
    print("Creating Basic product...")
    basic_product = stripe.Product.create(
        name="TuExpertoFiscal Basic",
        description="25 consultas/día, búsqueda en documentos, recordatorios",
        metadata={"plan": "basic"}
    )
    print(f"  Product: {basic_product.id}")

    basic_monthly = stripe.Price.create(
        product=basic_product.id,
        unit_amount=299,  # €2.99 in cents
        currency="eur",
        recurring={"interval": "month"},
        metadata={"plan": "basic", "period": "monthly"}
    )
    print(f"  Monthly: {basic_monthly.id} (€2.99/month)")

    basic_yearly = stripe.Price.create(
        product=basic_product.id,
        unit_amount=2999,  # €29.99 in cents
        currency="eur",
        recurring={"interval": "year"},
        metadata={"plan": "basic", "period": "yearly"}
    )
    print(f"  Yearly: {basic_yearly.id} (€29.99/year)")

    # Create Pro product
    print("\nCreating Pro product...")
    pro_product = stripe.Product.create(
        name="TuExpertoFiscal Pro",
        description="Consultas ilimitadas, todas las funciones, respuestas prioritarias",
        metadata={"plan": "pro"}
    )
    print(f"  Product: {pro_product.id}")

    pro_monthly = stripe.Price.create(
        product=pro_product.id,
        unit_amount=999,  # €9.99 in cents
        currency="eur",
        recurring={"interval": "month"},
        metadata={"plan": "pro", "period": "monthly"}
    )
    print(f"  Monthly: {pro_monthly.id} (€9.99/month)")

    pro_yearly = stripe.Price.create(
        product=pro_product.id,
        unit_amount=9999,  # €99.99 in cents
        currency="eur",
        recurring={"interval": "year"},
        metadata={"plan": "pro", "period": "yearly"}
    )
    print(f"  Yearly: {pro_yearly.id} (€99.99/year)")

    # Print .env values to add
    print("\n" + "=" * 60)
    print("Add these to your .env:")
    print("=" * 60)
    print(f"STRIPE_PRICE_BASIC_MONTHLY={basic_monthly.id}")
    print(f"STRIPE_PRICE_BASIC_YEARLY={basic_yearly.id}")
    print(f"STRIPE_PRICE_PRO_MONTHLY={pro_monthly.id}")
    print(f"STRIPE_PRICE_PRO_YEARLY={pro_yearly.id}")
    print("=" * 60)

    # Auto-update .env
    env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    env_path = os.path.abspath(env_path)

    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            content = f.read()

        replacements = {
            'STRIPE_PRICE_PREMIUM_MONTHLY=price_your_monthly_price_id': f'STRIPE_PRICE_BASIC_MONTHLY={basic_monthly.id}\nSTRIPE_PRICE_PRO_MONTHLY={pro_monthly.id}',
            'STRIPE_PRICE_PREMIUM_YEARLY=price_your_yearly_price_id': f'STRIPE_PRICE_BASIC_YEARLY={basic_yearly.id}\nSTRIPE_PRICE_PRO_YEARLY={pro_yearly.id}',
        }

        for old, new in replacements.items():
            content = content.replace(old, new)

        with open(env_path, 'w') as f:
            f.write(content)

        print(f"\n.env updated: {env_path}")

    # Update Supabase subscription_plans with Stripe price IDs
    print("\nUpdate Supabase subscription_plans:")
    print(f"  UPDATE subscription_plans SET stripe_price_id_monthly = '{basic_monthly.id}', stripe_price_id_yearly = '{basic_yearly.id}' WHERE name = 'basic';")
    print(f"  UPDATE subscription_plans SET stripe_price_id_monthly = '{pro_monthly.id}', stripe_price_id_yearly = '{pro_yearly.id}' WHERE name = 'pro';")


if __name__ == "__main__":
    setup_stripe()
