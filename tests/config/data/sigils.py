all_bad_cases = [
    # 1 item
    {"Sigils": {"blacklist": "monster_cold_resist"}},
    {"Sigils": {"blacklist": ["monster123_cold_resist"]}},
    {"Sigils": {"blacklist": ["monster_cold_resist", "test123"]}},
    {"Sigils": {"blacklist": ["monster_cold_resist"], "whitelist": ["monster_cold_resist"]}},
    {"Sigils": {"whitelist": ["monster123_cold_resist"]}},
    {"Sigils": {"whitelist": ["monster_cold_resist", "test123"]}},
]

all_good_cases = [
    # 1 item
    {"Sigils": {"blacklist": ["monster_cold_resist"]}},
    {"Sigils": {"whitelist": ["monster_cold_resist"]}},
    # 2 items
    {"Sigils": {"blacklist": ["monster_cold_resist"], "whitelist": ["monster_fire_resist"]}},
]
