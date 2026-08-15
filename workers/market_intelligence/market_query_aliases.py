from __future__ import annotations

# Natural-language Greek market phrases used for retrieval only.
# They never become taxonomy values; canonical taxonomy remains English/stable.
QUERY_ALIASES: dict[str, tuple[str, ...]] = {
    'Fashion & Accessories': ('ρούχα και αξεσουάρ', 'μόδα online'),
    'Apparel': ('ρούχα', 'γυναικεία ρούχα', 'ανδρικά ρούχα'),
    'Footwear': ('παπούτσια', 'αθλητικά παπούτσια', 'sneakers'),
    'Bags & Luggage': ('τσάντες', 'σακίδια', 'βαλίτσες'),
    'Jewelry & Watches': ('κοσμήματα', 'ρολόγια'),
    'Eyewear & Accessories': ('γυαλιά ηλίου', 'πορτοφόλια', 'ζώνες'),
    'Beauty & Personal Care': ('καλλυντικά και περιποίηση', 'προσωπική περιποίηση'),
    'Skincare': ('περιποίηση προσώπου', 'κρέμες προσώπου', 'serum προσώπου'),
    'Sun Care': ('αντηλιακά', 'αντηλιακό προσώπου', 'αντηλιακό σώματος'),
    'Makeup': ('μακιγιάζ', 'καλλυντικά μακιγιάζ'),
    'Hair Care': ('περιποίηση μαλλιών', 'σαμπουάν', 'θεραπεία μαλλιών'),
    'Fragrance': ('αρώματα', 'γυναικεία αρώματα', 'ανδρικά αρώματα'),
    'Personal Care': ('περιποίηση σώματος', 'προϊόντα προσωπικής υγιεινής'),
    'Health & Wellness': ('υγεία και ευεξία', 'προϊόντα ευεξίας'),
    'Supplements': ('συμπληρώματα διατροφής', 'βιταμίνες', 'πρωτεΐνη'),
    'Pharmacy & OTC': ('φαρμακείο online', 'παραφαρμακευτικά', 'μη συνταγογραφούμενα'),
    'Wellness & Recovery': ('αποκατάσταση σώματος', 'μασάζ', 'ορθοπεδικά βοηθήματα'),
    'Electronics & Technology': ('ηλεκτρονικά', 'τεχνολογία'),
    'Computers & Laptops': ('laptop', 'φορητοί υπολογιστές', 'υπολογιστές'),
    'Phones & Accessories': ('κινητά τηλέφωνα', 'smartphone', 'αξεσουάρ κινητών'),
    'TV & Audio': ('τηλεοράσεις', 'ακουστικά', 'ηχεία'),
    'Gaming': ('gaming', 'gaming pc', 'κονσόλες παιχνιδιών'),
    'Smart Home & Gadgets': ('έξυπνο σπίτι', 'smart home', 'gadgets'),
    'Home & Garden': ('σπίτι και κήπος', 'είδη σπιτιού'),
    'Furniture': ('έπιπλα', 'καναπέδες', 'τραπέζια'),
    'Home Decor': ('διακόσμηση σπιτιού', 'πίνακες τοίχου', 'διακοσμητικά'),
    'Kitchen & Dining': ('είδη κουζίνας', 'μαγειρικά σκεύη', 'κουζινικά'),
    'Bathroom': ('είδη μπάνιου', 'αξεσουάρ μπάνιου'),
    'Garden & Outdoor Living': ('είδη κήπου', 'έπιπλα κήπου', 'βεράντα'),
    'Home Appliances': ('οικιακές συσκευές', 'μικροσυσκευές', 'ηλεκτρικές συσκευές'),
    'Bedding & Textiles': ('στρώματα', 'μαξιλάρια', 'λευκά είδη'),
    'Sports & Outdoors': ('αθλητικά είδη', 'είδη outdoor'),
    'Fitness': ('όργανα γυμναστικής', 'fitness εξοπλισμός', 'βάρη γυμναστικής'),
    'Running': ('τρέξιμο', 'παπούτσια τρεξίματος', 'running'),
    'Cycling': ('ποδήλατα', 'ποδηλασία', 'αξεσουάρ ποδηλάτου'),
    'Camping & Hiking': ('camping', 'πεζοπορία', 'σκηνές camping'),
    'Sports Equipment': ('αθλητικός εξοπλισμός', 'μπάλες', 'ρακέτες'),
    'Kids & Baby': ('βρεφικά και παιδικά', 'είδη για παιδιά'),
    'Baby Care': ('βρεφικά είδη', 'πάνες', 'καρότσια μωρού'),
    'Kids Clothing': ('παιδικά ρούχα', 'βρεφικά ρούχα'),
    'Toys & Games': ('παιχνίδια', 'παιδικά παιχνίδια', 'lego'),
    'School Supplies': ('σχολικά είδη', 'σχολικές τσάντες', 'γραφική ύλη'),
    'Books & Education': ('βιβλία και εκπαίδευση', 'εκπαιδευτικά βιβλία'),
    'Books': ('βιβλία', 'ελληνικά βιβλία'),
    'Educational Materials': ('σχολικά βοηθήματα', 'εκπαιδευτικό υλικό'),
    'Courses & Training': ('online μαθήματα', 'σεμινάρια', 'επαγγελματική κατάρτιση'),
    'Food & Drink': ('τρόφιμα και ποτά', 'online supermarket'),
    'Grocery': ('τρόφιμα', 'είδη supermarket', 'παντοπωλείο online'),
    'Coffee & Tea': ('καφές', 'espresso', 'τσάι'),
    'Wine & Beverages': ('κρασί', 'ποτά', 'ροφήματα'),
    'Specialty Food': ('βιολογικά τρόφιμα', 'gourmet τρόφιμα', 'delicatessen'),
    'Travel': ('ταξίδια', 'διακοπές'),
    'Flights': ('αεροπορικά εισιτήρια', 'πτήσεις'),
    'Hotels & Accommodation': ('ξενοδοχεία', 'διαμονή', 'καταλύματα'),
    'Travel Packages & Activities': ('πακέτα διακοπών', 'εκδρομές', 'ταξιδιωτικές δραστηριότητες'),
    'Car Rental': ('ενοικίαση αυτοκινήτου', 'rent a car'),
    'Automotive': ('αυτοκίνητο', 'είδη αυτοκινήτου'),
    'Car Parts & Accessories': ('ανταλλακτικά αυτοκινήτου', 'αξεσουάρ αυτοκινήτου'),
    'Tyres & Wheels': ('ελαστικά αυτοκινήτου', 'ζάντες'),
    'Motorcycle': ('μοτοσυκλέτες', 'αξεσουάρ μηχανής', 'scooter'),
    'Car Care': ('περιποίηση αυτοκινήτου', 'λιπαντικά αυτοκινήτου'),
    'Pets': ('κατοικίδια', 'είδη κατοικιδίων'),
    'Pet Food': ('τροφή σκύλου', 'τροφή γάτας', 'τροφές κατοικιδίων'),
    'Pet Supplies': ('αξεσουάρ κατοικιδίων', 'είδη σκύλου', 'είδη γάτας'),
    'Pet Health': ('υγεία κατοικιδίων', 'αντιπαρασιτικά κατοικιδίων'),
    'Services & Digital': ('ψηφιακές υπηρεσίες', 'online υπηρεσίες'),
    'Software & SaaS': ('λογισμικό', 'saas', 'συνδρομητικές εφαρμογές'),
    'Hosting & Domains': ('web hosting', 'φιλοξενία ιστοσελίδων', 'domains'),
    'Finance & Insurance': ('ασφάλειες', 'τραπεζικές υπηρεσίες', 'δάνεια'),
    'Telecom & Utilities': ('πάροχοι internet', 'κινητή τηλεφωνία', 'πάροχοι ενέργειας'),
}


def market_query_terms(category: str, subcategory: str | None) -> list[str]:
    key = subcategory or category
    terms = list(QUERY_ALIASES.get(key, ()))
    if not terms:
        terms = [key]
    # Include canonical label as a fallback, but Greek natural phrases lead retrieval.
    if key not in terms:
        terms.append(key)
    return terms[:4]
