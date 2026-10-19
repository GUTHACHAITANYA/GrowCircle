"""
Local Government Directory (LGD) Master Data & Boundaries for Andhra Pradesh & Core States.
Contains official LGD state codes, district codes, sub-district/mandal codes, and approximate centroids.
"""

from typing import Any

LGD_STATES_DATA: list[dict[str, Any]] = [
    {
        "id": "AP",
        "name": "Andhra Pradesh",
        "lgd_code": 28,
        "min_lat": 12.6,
        "max_lat": 19.9,
        "min_lon": 76.7,
        "max_lon": 84.8,
    },
    {
        "id": "TS",
        "name": "Telangana",
        "lgd_code": 36,
        "min_lat": 15.8,
        "max_lat": 19.9,
        "min_lon": 77.2,
        "max_lon": 81.8,
    },
    {
        "id": "KA",
        "name": "Karnataka",
        "lgd_code": 29,
        "min_lat": 11.5,
        "max_lat": 18.5,
        "min_lon": 74.0,
        "max_lon": 78.6,
    },
    {
        "id": "TN",
        "name": "Tamil Nadu",
        "lgd_code": 33,
        "min_lat": 8.0,
        "max_lat": 13.6,
        "min_lon": 76.2,
        "max_lon": 80.4,
    },
]

# Districts and mandals with LGD codes and coordinates
LGD_AP_DISTRICTS_AND_MANDALS: dict[str, dict[str, Any]] = {
    "Guntur": {
        "lgd_code": 506,
        "mandals": [
            {"name": "Guntur", "lgd_code": 4912, "latitude": 16.3067, "longitude": 80.4365},
            {"name": "Tenali", "lgd_code": 4918, "latitude": 16.2430, "longitude": 80.6400},
            {"name": "Mangalagiri", "lgd_code": 4905, "latitude": 16.4300, "longitude": 80.5700},
            {"name": "Ponnur", "lgd_code": 4919, "latitude": 16.0667, "longitude": 80.5500},
            {"name": "Chebrolu", "lgd_code": 4917, "latitude": 16.1989, "longitude": 80.5303},
            {"name": "Prathipadu", "lgd_code": 4924, "latitude": 16.1833, "longitude": 80.3333},
            {"name": "Medikonduru", "lgd_code": 4913, "latitude": 16.3333, "longitude": 80.2500},
        ],
    },
    "Annamayya": {
        "lgd_code": 743,
        "mandals": [
            {"name": "Madanapalle", "lgd_code": 5012, "latitude": 13.5500, "longitude": 78.5000},
            {"name": "Somala", "lgd_code": 5025, "latitude": 13.4475, "longitude": 78.8686},
            {"name": "Rayachoti", "lgd_code": 5010, "latitude": 14.0500, "longitude": 78.7500},
            {"name": "Thamballapalle", "lgd_code": 5005, "latitude": 13.8333, "longitude": 78.4167},
            {"name": "Pileru", "lgd_code": 5019, "latitude": 13.6833, "longitude": 78.9333},
            {"name": "Valmikipuram", "lgd_code": 5016, "latitude": 13.6500, "longitude": 78.6333},
        ],
    },
    "NTR": {
        "lgd_code": 745,
        "mandals": [
            {"name": "Vijayawada Urban", "lgd_code": 4890, "latitude": 16.5062, "longitude": 80.6480},
            {"name": "Vijayawada Rural", "lgd_code": 4891, "latitude": 16.5200, "longitude": 80.6200},
            {"name": "Ibrahimpatnam", "lgd_code": 4885, "latitude": 16.5833, "longitude": 80.5167},
            {"name": "Nandigama", "lgd_code": 4875, "latitude": 16.7833, "longitude": 80.3000},
            {"name": "Jaggayyapeta", "lgd_code": 4870, "latitude": 16.8920, "longitude": 80.0980},
            {"name": "Mylavaram", "lgd_code": 4878, "latitude": 16.7667, "longitude": 80.6333},
            {"name": "Tiruvuru", "lgd_code": 4867, "latitude": 17.1167, "longitude": 80.6167},
        ],
    },
    "Anantapur": {
        "lgd_code": 502,
        "mandals": [
            {"name": "Anantapur", "lgd_code": 5030, "latitude": 14.6819, "longitude": 77.6006},
            {"name": "Gooty", "lgd_code": 5035, "latitude": 15.1167, "longitude": 77.6333},
            {"name": "Tadipatri", "lgd_code": 5038, "latitude": 14.9100, "longitude": 78.0100},
            {"name": "Uravakonda", "lgd_code": 5042, "latitude": 14.9500, "longitude": 77.2667},
            {"name": "Kalyandurg", "lgd_code": 5045, "latitude": 14.5500, "longitude": 77.1000},
            {"name": "Rayadurg", "lgd_code": 5048, "latitude": 14.7000, "longitude": 76.8667},
        ],
    },
    "Kurnool": {
        "lgd_code": 511,
        "mandals": [
            {"name": "Kurnool", "lgd_code": 5110, "latitude": 15.8281, "longitude": 78.0373},
            {"name": "Adoni", "lgd_code": 5115, "latitude": 15.6300, "longitude": 77.2700},
            {"name": "Yemmiganur", "lgd_code": 5120, "latitude": 15.7667, "longitude": 77.4833},
            {"name": "Alur", "lgd_code": 5125, "latitude": 15.3000, "longitude": 77.2333},
            {"name": "Pattikonda", "lgd_code": 5130, "latitude": 15.4000, "longitude": 77.5000},
            {"name": "Kodumur", "lgd_code": 5135, "latitude": 15.6833, "longitude": 77.7833},
        ],
    },
    "Tirupati": {
        "lgd_code": 751,
        "mandals": [
            {"name": "Tirupati Urban", "lgd_code": 5150, "latitude": 13.6288, "longitude": 79.4192},
            {"name": "Tirupati Rural", "lgd_code": 5151, "latitude": 13.6000, "longitude": 79.4000},
            {"name": "Chandragiri", "lgd_code": 5155, "latitude": 13.5833, "longitude": 79.3167},
            {"name": "Srikalahasti", "lgd_code": 5160, "latitude": 13.7500, "longitude": 79.7000},
            {"name": "Gudur", "lgd_code": 5165, "latitude": 14.1500, "longitude": 79.8500},
            {"name": "Venkatagiri", "lgd_code": 5170, "latitude": 13.9667, "longitude": 79.5833},
            {"name": "Sullurpeta", "lgd_code": 5175, "latitude": 13.7000, "longitude": 80.0167},
        ],
    },
    "East Godavari": {
        "lgd_code": 505,
        "mandals": [
            {"name": "Rajahmundry Urban", "lgd_code": 4840, "latitude": 17.0005, "longitude": 81.8040},
            {"name": "Rajahmundry Rural", "lgd_code": 4841, "latitude": 17.0200, "longitude": 81.7800},
            {"name": "Kadiam", "lgd_code": 4845, "latitude": 16.9167, "longitude": 81.8333},
            {"name": "Rajanagaram", "lgd_code": 4850, "latitude": 17.0833, "longitude": 81.9000},
            {"name": "Anaparthi", "lgd_code": 4855, "latitude": 16.9333, "longitude": 81.9500},
            {"name": "Korukonda", "lgd_code": 4860, "latitude": 17.1667, "longitude": 81.8167},
        ],
    },
    "Prakasam": {
        "lgd_code": 517,
        "mandals": [
            {"name": "Santhamaguluru", "lgd_code": 4980, "latitude": 16.0333, "longitude": 80.0333},
            {"name": "Ongole", "lgd_code": 4970, "latitude": 15.5057, "longitude": 80.0499},
            {"name": "Chirala", "lgd_code": 4975, "latitude": 15.8200, "longitude": 80.3500},
            {"name": "Addanki", "lgd_code": 4985, "latitude": 15.8167, "longitude": 79.9833},
            {"name": "Kandukur", "lgd_code": 4990, "latitude": 15.2167, "longitude": 79.9000},
            {"name": "Markapur", "lgd_code": 4995, "latitude": 15.7333, "longitude": 79.2833},
            {"name": "Giddalur", "lgd_code": 5000, "latitude": 15.3833, "longitude": 78.9333},
        ],
    },
}
