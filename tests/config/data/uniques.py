all_bad_cases = [
    ({"GlobalUniques": [{"minPower": -20}]}, "must be greater than zero"),  # Has to be above 0
    ({"GlobalUniques": [{"minGreaterAffixCount": 5}]}, "must be in [0, 4]"),  # Can't be greater than 4
    ({"GlobalUniques": [{"minPercentOfAspect": 110}]}, "must be less than or equal to 100"),  # Can't be above 100
]

all_good_cases = {
    "name": "good",
    "GlobalUniques": [{"minPower": 300}, {"minGreaterAffixCount": 4}, {"minPercentOfAspect": 100}],
}
