from enum import Enum


# The values will be overwritte depending on which language is loaded
class ItemType(Enum):
    Amulet = "amulet"
    Axe = "axe"
    Axe2H = "two-handed axe"
    Boots = "boots"
    Bow = "bow"
    ChestArmor = "chest armor"
    Crossbow2H = "crossbow"
    Dagger = "dagger"
    Elixir = "elixir"
    Focus = "focus"
    Glaive = "glaive"
    Gloves = "gloves"
    Helm = "helm"
    Legs = "pants"
    Mace = "mace"
    Mace2H = "two-handed mace"
    OffHandTotem = "totem"
    Polearm = "polearm"
    Quarterstaff = "quarterstaff"
    Ring = "ring"
    Scythe = "scythe"
    Scythe2H = "two-handed scythe"
    Shield = "shield"
    Staff = "staff"
    Sword = "sword"
    Sword2H = "two-handed sword"
    Tome = "tome"
    Wand = "wand"
    # Custom Types
    Compass = "compass"
    Consumable = "consumable"
    Gem = "gem"
    Incense = "incense"
    Material = "material"
    Rune = "rune"
    Sigil = "nightmare sigil"
    TemperManual = "temper manual"
    Tribute = "tribute"


def is_armor(item_type: ItemType) -> bool:
    return item_type in [
        ItemType.Boots,
        ItemType.ChestArmor,
        ItemType.Gloves,
        ItemType.Helm,
        ItemType.Legs,
    ]


def is_consumable(item_type: ItemType) -> bool:
    return item_type in [
        ItemType.Consumable,
        ItemType.Elixir,
        ItemType.Incense,
        ItemType.TemperManual,
    ]


def is_mapping(item_type: ItemType) -> bool:
    return item_type in [
        ItemType.Compass,
        ItemType.Sigil,
    ]


def is_jewelry(item_type: ItemType) -> bool:
    return item_type in [
        ItemType.Amulet,
        ItemType.Ring,
    ]


def is_socketable(item_type: ItemType) -> bool:
    return item_type in [
        ItemType.Gem,
        ItemType.Rune,
    ]


def is_weapon(item_type: ItemType) -> bool:
    return item_type in [
        ItemType.Axe,
        ItemType.Axe2H,
        ItemType.Bow,
        ItemType.Crossbow2H,
        ItemType.Dagger,
        ItemType.Focus,
        ItemType.Glaive,
        ItemType.Mace,
        ItemType.Mace2H,
        ItemType.OffHandTotem,
        ItemType.Polearm,
        ItemType.Quarterstaff,
        ItemType.Scythe,
        ItemType.Scythe2H,
        ItemType.Staff,
        ItemType.Sword,
        ItemType.Sword2H,
        ItemType.Tome,
        ItemType.Wand,
    ]
