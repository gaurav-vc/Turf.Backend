import os
import json
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from shop.models import Product

INITIAL_PRODUCTS = [
    {
        'name': 'FC Barcelona 2026 Home Custom Kit',
        'base_price': Decimal('1499.00'),
        'in_stock': True,
        'metadata': {
            'category': 'Jerseys',
            'sport': 'Football',
            'badge': 'Bestseller',
            'rating': 4.9,
            'reviews_count': 128,
            'is_customizable': True,
            'sizes': ['S', 'M', 'L', 'XL', 'XXL'],
            'image_url': 'https://images.unsplash.com/photo-1577223625816-7546f13df25d?w=800&auto=format&fit=crop&q=80',
            'features': ['Official Blaugrana Stripes', 'Breathable Dry-Fit Mesh', 'Custom Back Printing', 'Sublimated Team Crest'],
            'description_text': 'Authentic FC Barcelona custom team jersey engineered with sweat-wicking performance fabric. Personalize with your name and squad number.'
        }
    },
    {
        'name': 'Real Madrid Away Golden Edition Jersey',
        'base_price': Decimal('1599.00'),
        'in_stock': True,
        'metadata': {
            'category': 'Jerseys',
            'sport': 'Football',
            'badge': 'Trending',
            'rating': 4.9,
            'reviews_count': 94,
            'is_customizable': True,
            'sizes': ['S', 'M', 'L', 'XL', 'XXL'],
            'image_url': 'https://images.unsplash.com/photo-1522778119026-d647f0596c20?w=800&auto=format&fit=crop&q=80',
            'features': ['Royal Golden Accents', 'Ultra-light Hydrophobic Fabric', 'Custom Name & Number', 'Athletic Tailored Fit'],
            'description_text': 'Commemorative Real Madrid golden edition kit designed for high-intensity turf play and style.'
        }
    },
    {
        'name': 'India Box Cricket Pro Team Kit',
        'base_price': Decimal('1199.00'),
        'in_stock': True,
        'metadata': {
            'category': 'Jerseys',
            'sport': 'Cricket',
            'badge': 'Popular',
            'rating': 4.8,
            'reviews_count': 86,
            'is_customizable': True,
            'sizes': ['S', 'M', 'L', 'XL'],
            'image_url': 'https://images.unsplash.com/photo-1540747913346-19e32dc3e97e?w=800&auto=format&fit=crop&q=80',
            'features': ['High-Stretch Cricket Jersey', 'Fade-Resistant Sublimation', 'Customizable Name/Number', 'UV & Turf Resistant'],
            'description_text': 'Specialized box cricket team kit crafted for maximum agility, flexibility, and fast runs.'
        }
    },
    {
        'name': 'Nike Mercurial Superfly 9 Turf Studs',
        'base_price': Decimal('3499.00'),
        'in_stock': True,
        'metadata': {
            'category': 'Footwear',
            'sport': 'Football',
            'badge': 'Pro Choice',
            'rating': 4.9,
            'reviews_count': 110,
            'is_customizable': False,
            'sizes': ['UK 6', 'UK 7', 'UK 8', 'UK 9', 'UK 10', 'UK 11'],
            'image_url': 'https://images.unsplash.com/photo-1511556532299-8f662fc26c06?w=800&auto=format&fit=crop&q=80',
            'features': ['Multi-Directional Rubber Turf Lugs', 'Flyknit Dynamic Fit Collar', 'High Grip Cushioning', 'Durable Synthetic Upper'],
            'description_text': 'Elite turf football shoes offering explosive traction and pinpoint control on synthetic grass.'
        }
    },
    {
        'name': 'Puma Future Play TT Turf Shoes',
        'base_price': Decimal('2799.00'),
        'in_stock': True,
        'metadata': {
            'category': 'Footwear',
            'sport': 'Football',
            'badge': 'Top Rated',
            'rating': 4.7,
            'reviews_count': 64,
            'is_customizable': False,
            'sizes': ['UK 7', 'UK 8', 'UK 9', 'UK 10'],
            'image_url': 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=800&auto=format&fit=crop&q=80',
            'features': ['Low-Profile Multi-Stud Outsole', 'Soft Engineered Upper', 'EVA Shock Absorb Midsole', 'Snug Ankle Support'],
            'description_text': 'Engineered for playmakers on artificial turf with enhanced ball grip textures and comfort.'
        }
    },
    {
        'name': 'TurfArena Heavy Tennis Cricket Ball (Pack of 6)',
        'base_price': Decimal('549.00'),
        'in_stock': True,
        'metadata': {
            'category': 'Equipment',
            'sport': 'Cricket',
            'badge': 'Essential',
            'rating': 4.9,
            'reviews_count': 230,
            'is_customizable': False,
            'sizes': ['Pack of 6'],
            'image_url': 'https://images.unsplash.com/photo-1531415074868-036b1c57e359?w=800&auto=format&fit=crop&q=80',
            'features': ['Heavy Weight 125g Specs', 'Consistent True Bounce', 'High-Visibility Optic Yellow', 'Long-Lasting Felt Cover'],
            'description_text': 'Tournament-grade heavy tennis balls engineered specifically for box cricket turfs and tournaments.'
        }
    },
    {
        'name': 'SS Master 5000 Kashmir Willow Turf Bat',
        'base_price': Decimal('2299.00'),
        'in_stock': True,
        'metadata': {
            'category': 'Equipment',
            'sport': 'Cricket',
            'badge': 'Heavy Hitter',
            'rating': 4.8,
            'reviews_count': 72,
            'is_customizable': False,
            'sizes': ['Short Handle (Men)'],
            'image_url': 'https://images.unsplash.com/photo-1593341646782-e0b495cff86d?w=800&auto=format&fit=crop&q=80',
            'features': ['Hand-Selected Kashmir Willow', 'Thick 40mm Power Edges', 'Curved Blade for Aerial Hits', 'Comfort Chevron Grip'],
            'description_text': 'Power-hitting box cricket bat with thick edges, balanced pickup, and protective toe guard.'
        }
    },
    {
        'name': 'Adidas Predator Pro Goalkeeper Gloves',
        'base_price': Decimal('1699.00'),
        'in_stock': True,
        'metadata': {
            'category': 'Accessories',
            'sport': 'Football',
            'badge': 'Pro Grip',
            'rating': 4.8,
            'reviews_count': 53,
            'is_customizable': False,
            'sizes': ['Size 8', 'Size 9', 'Size 10'],
            'image_url': 'https://images.unsplash.com/photo-1600250395178-40fe752e5189?w=800&auto=format&fit=crop&q=80',
            'features': ['4mm URG 2.0 Latex Foam', 'High-Definition Rubber Punch Zone', 'Elastic Wrist Wrap Bandage', 'Negative Finger Cut'],
            'description_text': 'Match-ready goalkeeper gloves delivering superior grip and shock absorption in all weather.'
        }
    },
    {
        'name': 'Pro Anti-Slip Cushion Grip Socks (3-Pack)',
        'base_price': Decimal('499.00'),
        'in_stock': True,
        'metadata': {
            'category': 'Accessories',
            'sport': 'Multi-Sport',
            'badge': 'Best Value',
            'rating': 4.9,
            'reviews_count': 340,
            'is_customizable': False,
            'sizes': ['One Size (UK 6-11)'],
            'image_url': 'https://images.unsplash.com/photo-1586350977771-b3b0abd50c82?w=800&auto=format&fit=crop&q=80',
            'features': ['Hexagonal Silicone Non-Slip Pads', 'Blister Prevention Cushioning', 'Breathable Arch Compression', '3 Colors: Black, White, Navy'],
            'description_text': 'The #1 choice for turf athletes. Eliminates foot slippage inside football studs and cricket shoes.'
        }
    },
    {
        'name': 'Squad Training Bibs & Agility Cones Pack',
        'base_price': Decimal('899.00'),
        'in_stock': True,
        'metadata': {
            'category': 'Training',
            'sport': 'Multi-Sport',
            'badge': 'Club Pack',
            'rating': 4.7,
            'reviews_count': 41,
            'is_customizable': False,
            'sizes': ['Standard Set'],
            'image_url': 'https://images.unsplash.com/photo-1526676037777-05a232554f77?w=800&auto=format&fit=crop&q=80',
            'features': ['10 Reversible Neon Mesh Bibs', '10 Flexible Agility Saucer Cones', 'Tear-Resistant Polyester', 'Carry Bag Included'],
            'description_text': 'Complete training kit for team drills, tactical scrimmage games, and speed ladder workouts.'
        }
    }
]

def seed():
    created_count = 0
    updated_count = 0
    for p_data in INITIAL_PRODUCTS:
        desc_json = json.dumps(p_data['metadata'])
        product, created = Product.objects.get_or_create(
            name=p_data['name'],
            defaults={
                'base_price': p_data['base_price'],
                'in_stock': p_data['in_stock'],
                'description': desc_json
            }
        )
        if created:
            created_count += 1
        else:
            # Update description if it was blank
            if not product.description or not product.description.startswith('{'):
                product.description = desc_json
                product.base_price = p_data['base_price']
                product.save()
                updated_count += 1

    print(f"Seeding completed: {created_count} products created, {updated_count} updated.")

if __name__ == '__main__':
    seed()
