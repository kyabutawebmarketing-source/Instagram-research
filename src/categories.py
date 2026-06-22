"""Category → hashtag mapping used for influencer discovery."""

CATEGORY_HASHTAGS: dict[str, list[str]] = {
    "beauty": ["コスメ", "美容", "メイク"],
    "fashion": ["ファッション", "コーデ"],
    "parenting": ["子育て", "ベビー", "育児"],
    "fitness": ["ダイエット", "フィットネス"],
    "travel": ["旅行", "travel"],
    "gift": ["プレゼント", "ギフト"],
    "pet": ["ペット", "犬好き"],
}

CATEGORY_LABELS_JA: dict[str, str] = {
    "beauty": "美容・コスメ",
    "fashion": "ファッション",
    "parenting": "子育て・ベビー",
    "fitness": "ダイエット・フィットネス",
    "travel": "旅行",
    "gift": "プレゼント",
    "pet": "ペット",
}
