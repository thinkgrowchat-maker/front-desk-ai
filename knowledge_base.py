"""
The business's knowledge base.

This single file is the ENTIRE "brain" the assistant is allowed to answer from.
To point Front Desk AI at a different business, you only edit this file — the
retrieval and grounding logic stay exactly the same.

Each entry has:
  id       - a short stable identifier (shown as a citation in the UI)
  title    - human-readable label
  keywords - extra search terms that may not appear in the text itself
  text     - the guest-facing facts the model may use
"""

BUSINESS = {
    "name": "The Copper Kettle",
    "tagline": "Neighborhood farm-to-table bistro",
    "phone": "(555) 210-4488",
    "email": "hello@copperkettlebistro.com",
}

KNOWLEDGE_BASE = [
    {
        "id": "hours",
        "title": "Hours & Location",
        "keywords": ["hours", "open", "close", "closing", "time", "today",
                     "location", "address", "where", "directions", "sunday", "monday"],
        "text": (
            "The Copper Kettle is open Tuesday through Sunday. Lunch is served "
            "11:30am–2:30pm and dinner 5:00pm–10:00pm (the kitchen closes at 9:30pm). "
            "We are closed on Mondays. You'll find us at 428 Maple Street in the "
            "Old Mill district."
        ),
    },
    {
        "id": "reservations",
        "title": "Reservations & Walk-ins",
        "keywords": ["reservation", "reserve", "book", "booking", "table",
                     "walk-in", "walk in", "waitlist", "cancel", "availability"],
        "text": (
            "Reservations are recommended for dinner and can be booked online "
            "through our website or by phone. We hold reserved tables for 15 minutes "
            "past the booking time. Walk-ins are always welcome — we keep a few "
            "tables and the full bar open for them every night."
        ),
    },
    {
        "id": "parking",
        "title": "Parking",
        "keywords": ["parking", "park", "garage", "valet", "lot", "street", "car"],
        "text": (
            "There is free street parking on Maple Street and a public parking "
            "garage one block away on Cedar Avenue ($3 flat rate after 5pm). We do "
            "not offer valet, but the garage is a short, well-lit walk."
        ),
    },
    {
        "id": "menu",
        "title": "Menu & Cuisine",
        "keywords": ["menu", "food", "dishes", "specials", "seasonal", "dinner",
                     "lunch", "chef", "cuisine", "eat", "steak", "fish", "vegetarian"],
        "text": (
            "Our menu is farm-to-table and changes with the season. Current "
            "favorites include the wood-roasted half chicken, house pappardelle "
            "with wild mushrooms, and a daily catch from the coast. We also serve a "
            "rotating list of shared small plates and a seasonal dessert board."
        ),
    },
    {
        "id": "dietary",
        "title": "Dietary Options",
        "keywords": ["vegetarian", "vegan", "gluten", "gluten-free", "dairy",
                     "dietary", "plant based", "plant-based", "options", "nut",
                     "nuts", "allergy", "allergies", "allergic", "allergen",
                     "peanut", "shellfish"],
        "text": (
            "We always offer vegetarian and vegan dishes, and several plates can be "
            "prepared gluten-free. Our menu marks common allergens and the kitchen "
            "is happy to adapt dishes where possible. Guests with serious or "
            "life-threatening allergies should speak with our team directly so we "
            "can review preparation with the chef."
        ),
    },
    {
        "id": "private-events",
        "title": "Private Events",
        "keywords": ["private", "event", "party", "group", "large party", "buyout",
                     "buy out", "rehearsal", "corporate", "reception", "host",
                     "wedding", "birthday"],
        "text": (
            "We host private events in our Garden Room, which seats up to 40 guests, "
            "and offer full buyouts of the restaurant for larger gatherings. Custom "
            "menus and pricing are arranged case by case with our events coordinator."
        ),
    },
    {
        "id": "takeout",
        "title": "Takeout & Delivery",
        "keywords": ["takeout", "take out", "to go", "pickup", "pick up", "delivery",
                     "deliver", "delivered", "order online", "doordash", "uber eats"],
        "text": (
            "Takeout is available for the full menu and can be ordered by phone or "
            "online for pickup. We partner with DoorDash and Uber Eats for delivery "
            "within about a 3-mile radius during regular hours."
        ),
    },
    {
        "id": "payment",
        "title": "Payment",
        "keywords": ["payment", "pay", "credit card", "cash", "apple pay",
                     "google pay", "tip", "gratuity", "split", "check", "cashless"],
        "text": (
            "We accept all major credit cards, Apple Pay, and Google Pay. We are a "
            "cashless restaurant. A 20% service charge is added to parties of six or "
            "more."
        ),
    },
    {
        "id": "kids",
        "title": "Kids & Families",
        "keywords": ["kids", "children", "child", "family", "high chair",
                     "kids menu", "baby", "booster", "stroller"],
        "text": (
            "Families are very welcome. We offer a kids menu, high chairs, and "
            "booster seats, and the earlier dinner seating tends to be the most "
            "family-friendly."
        ),
    },
    {
        "id": "pets",
        "title": "Dogs & Pets",
        "keywords": ["dog", "dogs", "pet", "pets", "patio", "service animal", "puppy"],
        "text": (
            "Well-behaved dogs are welcome on our outdoor patio (weather "
            "permitting) and we'll happily bring a water bowl. Service animals are "
            "welcome throughout the restaurant."
        ),
    },
    {
        "id": "gift-cards",
        "title": "Gift Cards",
        "keywords": ["gift card", "gift certificate", "voucher", "present", "gift"],
        "text": (
            "Gift cards are available in any amount and can be purchased in person "
            "or through our website. They never expire and can be used toward "
            "dining, takeout, or private events."
        ),
    },
    {
        "id": "accessibility",
        "title": "Accessibility",
        "keywords": ["accessible", "wheelchair", "accessibility", "ramp", "restroom",
                     "disabled", "ada", "mobility"],
        "text": (
            "Our dining room and patio are wheelchair accessible via a ramp at the "
            "Maple Street entrance, and we have an accessible restroom. Please let "
            "us know of any accommodations we can arrange in advance."
        ),
    },
    {
        "id": "atmosphere",
        "title": "Atmosphere & Dress Code",
        "keywords": ["dress code", "dress", "atmosphere", "attire", "casual",
                     "music", "noise", "romantic", "ambiance", "vibe"],
        "text": (
            "The Copper Kettle has a relaxed, rustic-modern atmosphere. There is no "
            "formal dress code — most guests come smart-casual. Evenings feature low "
            "background music that keeps conversation easy."
        ),
    },
    {
        "id": "contact",
        "title": "Contact the Team",
        "keywords": ["phone", "call", "email", "contact", "reach", "manager",
                     "team", "speak to someone", "human"],
        "text": (
            "You can reach our team by phone at {phone} or by email at {email}. "
            "For catering and private events, ask for our events coordinator."
        ).format(phone=BUSINESS["phone"], email=BUSINESS["email"]),
    },
]
