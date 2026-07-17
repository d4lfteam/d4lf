import re

BUILD_GUIDE_BASE_URL = "https://maxroll.gg/d4/build-guides/"
BUILD_SCRIPT_PREFIX = "window.__remixContext = "
PLANNER_API_BASE_URL = "https://planners.maxroll.gg/profiles/d4/"
PLANNER_API_DATA_URL = "https://assets-ng.maxroll.gg/d4-tools/game/data.min.json?39e88625"
PLANNER_API_REGEX = re.compile(r'(https://maxroll\.gg/d4/planner/[^"|\\]*)')
PLANNER_BASE_URL = "https://maxroll.gg/d4/planner/"
SCRIPT_XPATH = "//div[@id='root']/script"
SKILL_RANK_AFFIX_KEY_REGEX = re.compile(r"(?:_Category_|_Special_)(?P<label>[A-Za-z0-9]+)")
SKILL_RANK_BONUS_FORMULAS = {"GearAffix_SkillRankBonus", "GearAffix_SkillRankBonus_1to2"}
SKILL_RANK_DESC_LABEL_REGEX = re.compile(r"\{c_important\}([^{}]+)\{/c\}\s+Skills")
