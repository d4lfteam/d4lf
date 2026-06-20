all_bad_cases = [
    ({"GlobalUniques": [{"minPower": -20}]}, "Extra inputs are not permitted"),
    ({"GlobalUniques": [{"minGreaterAffixCount": 5}]}, "Extra inputs are not permitted"),
    ({"GlobalUniques": [{"minPercentOfAspect": 110}]}, "Extra inputs are not permitted"),
    ({"GlobalUniques": [{"itemType": ["helm"]}]}, "Extra inputs are not permitted"),
]

all_good_cases = {"name": "good", "GlobalUniques": [{"profileAlias": "good"}]}
