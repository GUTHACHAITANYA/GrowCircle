"""
Phonetic pronunciation dictionaries, number/currency synthesizers,
and prerecorded phrase catalogues for Telugu, Hindi, Gujarati, and English.
"""

# Pronunciation dictionaries for crops across languages
CROP_PRONUNCIATION: dict[str, dict[str, str]] = {
    "banana": {
        "en": "Banana",
        "te": "అరటిపండు",
        "hi": "केला",
        "gu": "કેળા",
    },
    "tomato": {
        "en": "Tomato",
        "te": "టమాటా",
        "hi": "टमाटर",
        "gu": "ટામેટાં",
    },
    "onion": {
        "en": "Onion",
        "te": "ఉల్లిపాయ",
        "hi": "प्याज",
        "gu": "ડુંગળી",
    },
}

# Phonetic pronunciation dictionaries for Mandi locations
MANDI_PRONUNCIATION: dict[str, dict[str, str]] = {
    "ap-guntur-01": {
        "en": "Guntur Fruit Market",
        "te": "గుంటూరు మార్కెట్",
        "hi": "गुंटूर मंडी",
        "gu": "ગુંટૂર માર્કેટ",
    },
    "ap-tenali-01": {
        "en": "Tenali Agricultural Market",
        "te": "తెనాలి మార్కెట్",
        "hi": "तेनाली मंडी",
        "gu": "તેનાલી માર્કેટ",
    },
    "ap-vijayawada-01": {
        "en": "Vijayawada Wholesale Mandi",
        "te": "విజయవాడ హోల్‌సేల్ మార్కెట్",
        "hi": "विजयवाड़ा थोक मंडी",
        "gu": "વિજયવાડા જથ્થાબંધ માર્કેટ",
    },
    "ap-tirupati-01": {
        "en": "Tirupati Mandi",
        "te": "తిరుపతి మార్కెట్",
        "hi": "तिरुपति मंडी",
        "gu": "તિરુપતિ માર્કેટ",
    },
    "ap-kurnool-01": {
        "en": "Kurnool Market",
        "te": "కర్నూలు మార్కెట్",
        "hi": "कर्नूल मंडी",
        "gu": "કર્નૂલ માર્કેટ",
    },
}

# District code keypad map: 1=Guntur, 2=NTR/Vijayawada, 3=Tirupati, 4=Kurnool
DISTRICT_KEYPAD_MAP: dict[str, dict[str, str]] = {
    "1": {
        "key": "guntur",
        "en": "Guntur",
        "te": "గుంటూరు",
        "hi": "गुंटूर",
        "gu": "ગુંટૂર",
        "lat": "16.3067",
        "lng": "80.4365",
    },
    "2": {
        "key": "ntr",
        "en": "NTR Vijayawada",
        "te": "ఎన్టీఆర్ విజయవాడ",
        "hi": "एनटीआर विजयवाड़ा",
        "gu": "એનટીઆર વિજયવાડા",
        "lat": "16.5062",
        "lng": "80.6480",
    },
    "3": {
        "key": "tirupati",
        "en": "Tirupati",
        "te": "తిరుపతి",
        "hi": "तिरुपति",
        "gu": "તિરુપતિ",
        "lat": "13.6288",
        "lng": "79.4192",
    },
    "4": {
        "key": "kurnool",
        "en": "Kurnool",
        "te": "కర్నూలు",
        "hi": "कर्नूल",
        "gu": "કર્નૂલ",
        "lat": "15.8281",
        "lng": "78.0373",
    },
}

# Standard Prerecorded Phrases Catalogue
PRERECORDED_PHRASES: dict[str, dict[str, str]] = {
    "welcome": {
        "en": "Welcome to GrowCircle, farm to everyone, full circle.",
        "te": "గ్రో సర్కిల్ కు స్వాగతం. రైతు నుండి ప్రతిఒక్కరికీ, సంపూర్ణ వలయం.",
        "hi": "ग्रो सर्कल में आपका स्वागत है. खेत से हर घर तक, पूरा घेरा.",
        "gu": "ગ્રો સર્કલમાં તમારું સ્વાગત છે. ખેતરથી દરેક સુધી, સંપૂર્ણ વર્તુળ.",
    },
    "language_menu": {
        "en": "For Telugu, press 1. For Hindi, press 2. For Gujarati, press 3.",
        "te": "తెలుగు కోసం 1 నొక్కండి. హిందీ కోసం 2 నొక్కండి. గుజరాతీ కోసం 3 నొక్కండి.",
        "hi": "तेलुगु के लिए 1 दबाएं. हिंदी के लिए 2 दबाएं. गुजराती के लिए 3 दबाएं.",
        "gu": "તેલુગુ માટે 1 દબાવો. હિન્દી માટે 2 દબાવો. ગુજરાતી માટે 3 દબાવો.",
    },
    "district_prompt": {
        "en": "Please choose your district: Press 1 for Guntur, 2 for NTR Vijayawada, 3 for Tirupati, 4 for Kurnool.",
        "te": "మీ జిల్లాను ఎంచుకోండి: గుంటూరు కోసం 1, విజయవాడ కోసం 2, తిరుపతి కోసం 3, కర్నూలు కోసం 4 నొక్కండి.",
        "hi": "अपना जिला चुनें: गुंटूर के लिए 1, विजयवाड़ा के लिए 2, तिरुपति के लिए 3, कर्नूल के लिए 4 दबाएं.",
        "gu": "તમારો જિલ્લો પસંદ કરો: ગુંટૂર માટે 1, વિજયવાડા માટે 2, તિરુપતિ માટે 3, કર્નૂલ માટે 4 દબાવો.",
    },
    "crop_menu": {
        "en": "Press 1 for Banana prices today.",
        "te": "నేటి అరటిపండు ధరల కోసం 1 నొక్కండి.",
        "hi": "आज के केले के भाव के लिए 1 दबाएं.",
        "gu": "આજના કેળાના ભાવ માટે 1 દબાવો.",
    },
    "post_action_menu": {
        "en": "Press 1 to sell produce, 2 for transport, 9 to repeat prices.",
        "te": "పంట అమ్మడానికి 1 నొక్కండి, రవాణా కోసం 2 నొక్కండి, ధరలు మళ్ళీ వినడానికి 9 నొక్కండి.",
        "hi": "फसल बेचने के लिए 1 दबाएं, परिवहन के लिए 2 दबाएं, भाव दोबारा सुनने के लिए 9 दबाएं.",
        "gu": "પાક વેચવા માટે 1 દબાવો, ટ્રાન્સપોર્ટ માટે 2 દબાવો, ભાવ ફરી સાંભળવા માટે 9 દબાવો.",
    },
    "sell_acknowledged": {
        "en": "Your sell request has been recorded. Verified buyers will contact you shortly. Thank you for using GrowCircle.",
        "te": "మీ పంట అమ్మకం అభ్యర్థన నమోదైంది. ధృవీకరించబడిన కొనుగోలుదారులు త్వరలోనే మిమ్మల్ని సంప్రదిస్తారు. గ్రో సర్కిల్ ఉపయోగించినందుకు ధన్యవాదాలు.",
        "hi": "आपकी फसल बिक्री का अनुरोध दर्ज हो गया है. सत्यापित खरीदार जल्द ही संपर्क करेंगे. ग्रो सर्कल का उपयोग करने के लिए धन्यवाद.",
        "gu": "તમારી પાક વેચાણ વિનંતી નોંધી લેવામાં આવી છે. ચકાસાયેલ ખરીદદારો ટૂંક સમયમાં સંપર્ક કરશે. ગ્રો સર્કલનો ઉપયોગ કરવા બદલ આભાર.",
    },
    "transport_acknowledged": {
        "en": "Your transport request has been recorded. Verified local drivers will receive your pickup lead. Thank you for using GrowCircle.",
        "te": "మీ రవాణా అభ్యర్థన నమోదైంది. స్థానిక డ్రైవర్లకు మీ వివరాలు పంపబడతాయి. గ్రో సర్కిల్ ఉపయోగించినందుకు ధన్యవాదాలు.",
        "hi": "आपके परिवहन का अनुरोध दर्ज हो गया है. स्थानीय ड्राइवरों को सूचना दी जाएगी. ग्रो सर्कल का उपयोग करने के लिए धन्यवाद.",
        "gu": "તમારી ટ્રાન્સપોર્ટ વિનંતી નોંધી લેવામાં આવી છે. સ્થાનિક ડ્રાઇવરોને જાણ કરવામાં આવશે. ગ્રો સર્કલનો ઉપયોગ કરવા બદલ આભાર.",
    },
    "no_prices": {
        "en": "Sorry, no prices available for this district today.",
        "te": "క్షమించండి, నేడు ఈ జిల్లాకు ధరలు అందుబాటులో లేవు.",
        "hi": "क्षमा करें, आज इस जिले के भाव उपलब्ध नहीं हैं.",
        "gu": "માફ કરશો, આજે આ જિલ્લા માટે ભાવ ઉપલબ્ધ નથી.",
    },
}


def get_crop_spoken_name(crop_id: str, lang: str = "te") -> str:
    """Returns phonetically localized crop name."""
    c_info = CROP_PRONUNCIATION.get(crop_id.lower().strip())
    if c_info:
        return c_info.get(lang, c_info.get("en", crop_id))
    return crop_id


def get_mandi_spoken_name(mandi_id: str, default_name: str, lang: str = "te") -> str:
    """Returns phonetically localized mandi name."""
    m_info = MANDI_PRONUNCIATION.get(mandi_id)
    if m_info:
        return m_info.get(lang, default_name)

    # Search by default_name substring in English pronunciation
    if default_name:
        d_lower = default_name.lower().strip()
        for info in MANDI_PRONUNCIATION.values():
            if d_lower in info.get("en", "").lower():
                return info.get(lang, default_name)

    return default_name or "మార్కెట్"


def format_price_spoken(price_per_kg: float, lang: str = "te") -> str:
    """
    Formats price in verbal currency words per language.
    e.g. 25.5 -> '25 రూపాయల 50 పైసలు' or '25 rupees 50 paise'
    """
    rupees = int(price_per_kg)
    paise = int(round((price_per_kg - rupees) * 100))

    if lang == "te":
        if paise > 0:
            return f"కిలో {rupees} రూపాయల {paise} పైసలు"
        return f"కిలో {rupees} రూపాయలు"
    elif lang == "hi":
        if paise > 0:
            return f"{rupees} रुपये {paise} पैसे प्रति किलो"
        return f"{rupees} रुपये प्रति किलो"
    elif lang == "gu":
        if paise > 0:
            return f"કિલોના {rupees} રૂપિયા {paise} પૈસા"
        return f"કિલોના {rupees} રૂપિયા"
    else:  # en
        if paise > 0:
            return f"{rupees} rupees and {paise} paise per kilo"
        return f"{rupees} rupees per kilo"


def build_mandi_prices_spoken_summary(
    mandis_data: list[dict],
    crop_id: str = "banana",
    lang: str = "te",
) -> str:
    """
    Builds the complete verbal mandi price broadcast under 1 minute.
    Stitches phonetically matched mandi names, crop name, and prices.
    """
    crop_name = get_crop_spoken_name(crop_id, lang)

    if not mandis_data:
        return PRERECORDED_PHRASES["no_prices"].get(lang, "No prices found.")

    if lang == "te":
        header = f"నేటి {crop_name} ధరలు:"
    elif lang == "hi":
        header = f"आज के {crop_name} के भाव:"
    elif lang == "gu":
        header = f"આજના {crop_name}ના ભાવ:"
    else:
        header = f"Today's {crop_name} prices:"

    lines = [header]
    for idx, item in enumerate(mandis_data[:3], 1):
        raw_name = item.get("mandi_name") or item.get("name") or ""
        m_name = get_mandi_spoken_name(str(item.get("mandi_id", "")), raw_name, lang)

        price_val = (
            item.get("modal_price_kg")
            if item.get("modal_price_kg") is not None
            else item.get("modal_price_per_kg", 0.0)
        )
        price_str = format_price_spoken(float(price_val), lang)
        dist_km = round(float(item.get("distance_km") or 0.0), 1)

        if lang == "te":
            lines.append(f"{idx}. {m_name}, దూరం {dist_km} కిలోమీటర్లు, ధర {price_str}.")
        elif lang == "hi":
            lines.append(f"{idx}. {m_name}, दूरी {dist_km} किलोमीटर, भाव {price_str}.")
        elif lang == "gu":
            lines.append(f"{idx}. {m_name}, અંતર {dist_km} કિલોમીટર, ભાવ {price_str}.")
        else:
            lines.append(f"{idx}. {m_name}, distance {dist_km} km, price {price_str}.")

    return " ".join(lines)
