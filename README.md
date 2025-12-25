# ![logo](assets/logo.png)

Filter items and sigils in your inventory based on affixes, aspects and thresholds of their values. For questions,
feature request or issue reports join the [discord](https://discord.gg/YyzaPhAN6T) or use github issues.

![sample](assets/thumbnail.jpg)

## Features

- Filter items in inventory and stash
- Filter by item type, item power and greater affix count
- Filter by affix and their values
- Filter uniques by their affix and aspect values
- Filter sigils by blacklisting and whitelisting locations and affixes
- Filter tributes by name or rarity
- Automatically marks all common, magic, and optionally rare gear as junk
- Quickly move items from your stash or inventory
- Supported resolutions are all aspect ratios between 16:10 and 21:9

## How to Setup

### Game Settings

- Game Language must be English
- IMPORTANT: Advanced Tooltip Information must be enabled in Options > Gameplay > Gameplay. If you don't do this then item parsing will be very inconsistent and you will receive no warning something is wrong.
- Font scale in Graphics settings must be small or medium
- HDR makes the screen too bright and D4LF is unable to read the state of some items on screen. It must be disabled.
- Use Screen Reader must be enabled in Options > Accessibility
- 3rd Party Screen Reader must be enabled in Options > Accessibility

### Installation and quick start guide

- Download and extract the latest version (.zip) from the releases: https://github.com/d4lfteam/d4lf/releases
- Copy `saapi64.dll` from the downloaded folder to your "Diablo IV" directory
  - To find your D4 directory:
    - In Battle.net, click the gear icon next to the Play button and select "Open in Explorer"
    - In Steam, right click the game, select Manage > Browse local files
- Generate a profile of what you want to filter for. To do so you have a few options:
  - Open gui.bat and import a profile by pasting a build page from popular planner websites
  - Take one someone else has generated from our [discord](https://discord.gg/YyzaPhAN6T)
  - Create one yourself by looking at the [examples](#how-to-filter--profiles) below
- If downloaded or created manually, place the profile in the `C:/Users/<WINDOWS_USER>/.d4lf/profiles` folder. The GUI
  importer has a button to open this folder directly. If imported they are placed there automatically.
- Run gui.bat and use the GUI config tab to configure the profiles. Select the '...' next to profiles to activate which
  profiles you want to use.
- Ensure all [game settings](#game-settings) are configured properly.
- Execute d4lf.exe and launch Diablo 4.
- Use the hotkeys listed in d4lf.exe to run filtering. By default, F11 will run the loot filter and filter your items.
- For most common issues, if something is wrong, you will see an error or warning when you start d4lf.exe

### Updating an existing installation

All configurations are stored in a separate location so all you need to do is download the newest version and delete your old version. This can be done manually by downloading from the [releases page](https://github.com/d4lfteam/d4lf/releases) or by running autoupdater.bat.

Your profiles and configuration should continue to work. The only exception to this is if the major version of the release changes. In that case, a change was made that will make previous profiles no longer work.

Example 1: You're on version 5.1.14 and updating to 5.2.0. Your profiles will continue to work fine.

Example 2: You're on version 5.1.14 and updating to 6.0.0. Your profiles will no longer work and you'll need to update or re-import them on the newest version.

### Common problems

- The GUI crashes immediately upon opening, with no error message given
  - This almost always means there is an issue in your params.ini. Delete the file and then open the GUI and configure
    your params.ini through the config tab. Using the GUI for configuration will ensure the file is always accurate.
- Mouse control isn't possible
  - Due to your local windows settings, the tool might not be able to control the mouse. Just run the tool as admin
    and it should work. If you don't want to run it as admin, you can disable the mouse control in the params.ini
    by setting `vision_mode_only` to `true`.
- Steam user: The tool shows a warning saying "TTS connection has not been made yet." but I've set everything up correctly.
  - If you're seeing this error, it means D4LF has found the DLL is in the correct location but the TTS connection is
    still not being made. This is most likely due to an issue with your windows user not allowing Diablo to connect to
    the third party screen reader. The following steps should resolve it:
    - Set Diablo 4 to run as administrator. First, navigate to your Diablo 4 directory. You can get there through Steam by right clicking on the game and
      choosing Properties. In that menu, go to Installed Files and hit Browse. Right-click on Diablo IV.exe and go to Properties. In the Compatibility tab, check the box
      that says "Run this program as an administrator"
    - Run Diablo 4 again through Steam and see if that resolved the issue.
    - If it did not, set Steam to run as administrator as well and make sure you are running Diablo through Steam. This should resolve the issue.

### TTS

D4 uses a third-party TTS engine called Tolk. Tolk has a feature that allows custom third-party TTS DLLs to be loaded.
D4 automatically loads the DLL, which actually just sends the text to another application rather than reading it aloud.
This is similar to having a Braille TTS application for D4.

### Configs

The config folder in `C:/Users/<WINDOWS_USER>/.d4lf` contains:

- **profiles/\*.yaml**: These files determine what should be filtered. Profiles created by the GUI will be placed here
  automatically.
- **params.ini**: Different hotkey settings and number of chest stashes that should be looked at. Management of this
  file should be done through the GUI.

### params.ini

| [general]                                         | Description                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| profiles                                          | A set of profiles separated by comma. d4lf will look for these yaml files in config/profiles and in C:/Users/WINDOWS_USER/.d4lf/profiles                                                                                                                                                                                                                                                                                                 |
| auto_use_temper_manuals                           | When using the loot filter, should found temper manuals be automatically used? Note: Will not work with stash open.                                                                                                                                                                                                                                                                                                                      |
| browser                                           | Which browser to use to get builds, please make sure you pick an installed browser: chrome, edge or firefox are currently supported.                                                                                                                                                                                                                                                                                                     |
| check_chest_tabs                                  | Which chest tabs will be checked and filtered for items in case chest is open when starting the filter. You need to buy all slots. Counting is done left to right. E.g. 1,2,4 will check tab 1, tab 2, tab 4                                                                                                                                                                                                                             |
| full_dump                                         | When using the import build feature, whether to use the full dump (e.g. contains all filter items) or not                                                                                                                                                                                                                                                                                                                                |
| handle_cosmetics                                  | How to handle new cosmetics that do not match any filter and are not aspect upgrades. `ignore` will ignore them, `junk` will mark them as junk                                                                                                                                                                                                                                                                                           |
| handle_uniques                                    | How to handle uniques that do not match any filter. This property does not apply to filtered uniques. All mythics are favorited regardless of filter. <br/>- `favorite`: Mark the unique as favorite and vision mode will show it as green (default)<br/>- `ignore`: Do nothing with the unique and vision mode will show it as green<br/>- `junk`: Mark any uniques that don't match any filters as junk and show as red in vision mode |
| ignore_escalation_sigils                          | When filtering Sigils, should escalation sigils be ignored?                                                                                                                                                                                                                                                                                                                                                                              |
| junk_rares                                        | When filtering rares, should they be automatically makred as junk? Note: If set to false, rares with socketed gems may have unexpected results when being filtered                                                                                                                                                                                                                                                                       |
| keep_aspects                                      | - `all`: Keep all legendary items <br>- `upgrade`: Keep all legendary items that upgrade your codex of power. If the item matches no profile, it will be highlighted in orange <br>- `none`: Keep no legendary items based on aspect (they are still filtered!) <br>-                                                                                                                                                                    |
| mark_as_favorite                                  | Whether to favorite matched items or not. Defaults to true                                                                                                                                                                                                                                                                                                                                                                               |
| max_stash_tabs                                    | The maximum number of stash tabs you have available to you if you bought them all. If you own the Lord of Hatred expansion you should choose 7.                                                                                                                                                                                                                                                                                          |
| minimum_overlay_font_size                         | The minimum font size for the vision overlay, specifically the green text that shows which filter(s) are matching. Note: For small profile names, the font may actually be larger than this size but will never go below this size.                                                                                                                                                                                                      |
| move_to_inv_item_type<br/>move_to_stash_item_type | Which types of items to move when using fast move functionality. Will only affect tabs defined in check_chest_tabs. You can select more than one option. <br>- `favorites`: Move favorites only <br>- `junk`: Move junk only <br>- `unmarked`: Only items not marked as favorite or junk <br>- `everything`: Move everything                                                                                                             |
| run_vision_mode_on_startup                        | If the vision mode should automatically start when starting d4lf. Otherwise has to be started manually with the vision button or the hotkey                                                                                                                                                                                                                                                                                              |
| s7_do_not_junk_ancestral_legendaries              | Do not mark ancestral legendaries as junk. This is to help with the season 7 Slayer seasonal challenge "Precious Shards"                                                                                                                                                                                                                                                                                                                 |
| vision_mode_type                                  | Which vision mode you would like to use?. `highlight_matches` does the classic green highlighting of affixes on screen, but is slightly slower. `fast` just puts green text on screen but is very fast and works with controllers.                                                                                                                                                                                                       |

| [char]    | Description                       |
| --------- | --------------------------------- |
| inventory | Your hotkey for opening inventory |

| [advanced_options]           | Description                                                                                                                                       |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| move_to_inv                  | Hotkey for moving items from stash to inventory                                                                                                   |
| move_to_chest                | Hotkey for moving items from inventory to stash                                                                                                   |
| run_filter                   | Hotkey to start/stop filtering items                                                                                                              |
| run_filter_force_refresh     | Hotkey to start/stop filtering items with a force refresh. All item statuses will be reset                                                        |
| run_vision_mode              | Hotkey to start/stop vision mode                                                                                                                  |
| force_refresh_only           | Hotkey to reset all item statuses without running a filter after                                                                                  |
| exit_key                     | Hotkey to exit d4lf.exe                                                                                                                           |
| log_lvl                      | Logging level. Can be any of [debug, info, warning, error, critical]                                                                              |
| process_name                 | Process name of the D4 app. Defaults to "Diablo IV.exe". In case of using some remote play this might need to be adapted                          |
| vision_mode_only             | If set to true, only the vision mode will be available. All functionality that clicks the screen is disabled.                                     |
| fast_vision_mode_coordinates | If you are using fast vision mode, provide the location on screen where you want the overlay to appear. For example, you could provide (500, 800) |

### GUI

Documentation is not yet finished. For now, it should be self-explanatory. Just start `gui.bat` in the archive.

Current functionality:

- Import builds from maxroll/d4builds/mobalytics
- Complete management of your params.ini through the config tab
- A beta version of a manual profile editor/creator

Each tab gives further instructions on how to use it and what kind of input it expects.

## How to filter / Profiles

All profiles define whitelist filters. If no filter included in your profiles matches the item, it will be discarded.

Your config files will be validated on startup and will prevent the program from starting if the structure or syntax is
incorrect. The error message will provide hints about the specific problem.

The following sections will explain each type of filter that you can specify in your profiles. How you define them in
your YAML files is up to you; you can put all of these into just one file or have a dedicated file for each type of
filter, or even split the same type of filter over multiple files. Ultimately, all profiles specified in
your `params.ini` will be used to determine if an item should be kept. If one of the profiles wants to keep the item, it
will be kept regardless of the other profiles. Similarly, if a filter is missing in all profiles (e.g., there is
no `Sigils` section in any profile), all corresponding items (in this case, sigils) will be kept.

### Affix / Unique Aspect Filter Syntax

You have three choices on how to specify aspects or affixes of an item:

- You can use the shorthand and just specify the aspect name
- For more sophisticated filtering, you can use the following syntax: `[NAME, THRESHOLD, CONDITION]`. The
  condition can be any of `[larger, smaller]` and defaults to `larger` if no value is given.
- Affixes generated through the importer have a different format but function the exact same. An
  example of an imported affix is `{name: dexterity, value: 33, comparison: larger}`. This is completely interchangeable
  with the shorthand notation.

As we recommend using the importer for a base version of your build, even if you intend to then manually create your own
build, the examples below will use the same format as the importer.

<details><summary>Examples</summary>

```yaml

# Filter for attack speed
- { name: attack_speed }
# Filter for attack speed larger than 4
- { name: attack_speed, value: 4 }
# Filter for attack speed smaller than 4
- { name: attack_speed, value: 4, comparison: smaller }

# Below is the older shorthand, which is still valid to use
# Filter for attack speed
- attack_speed
# Filter for attack speed larger than 4
- [ attack_speed, 4 ]
# Filter for attack speed smaller than 4
- [ attack_speed, 4, smaller ]
```

</details>

### Affixes

Affixes are defined by the top-level key `Affixes`. It contains a list of filters that you want to apply. Each filter
has a name and can filter for any combination of the following:

- `itemType`: The name of the type or a list of multiple types.
  See [assets/lang/enUS/item_types.json](assets/lang/enUS/item_types.json)
- `minPower`: Minimum item power
- `minGreaterAffixCount`: Minimum number of greater affixes. Note that this is on the overall item and independent
  of `affixPool`
- `affixPool`: A list of multiple different rulesets to filter for. Each ruleset must be fulfilled or the item is
  discarded
  - `count`: Define a list of affixes (see [syntax](#affix--aspects-filter-syntax)) and
    optionally `minCount`, `maxCount` and `minGreaterAffixCount`
    - `minCount`: specifies the minimum number of affixes that must match the item. defaults to amount of specified
      affixes
    - `maxCount` specifies the maximum number of affixes that must match the item. defaults to amount of specified
      affixes
    - `minGreaterAffixCount`: specifies the minimum number of greater affixes inside this count group. defaults
      to `0`
- `inherentPool`: The same rules as for `affixPool` apply, but this is evaluated against the inherent affixes of the
  item

<details><summary>Config Examples</summary>

```yaml
Affixes:
  # Search for chest armor and pants that are at least item level 725 and have at least 3 affixes of the affixPool
  - NiceArmor:
      itemType: [ chest armor, pants ]
      minPower: 725
      affixPool:
        - count:
            - { name: dexterity, value: 33 }
            - { name: damage_reduction, value: 5 }
            - { name: lucky_hit_chance, value: 3 }
            - { name: total_armor, value: 9 }
            - { name: maximum_life, value: 700 }
          minCount: 3

  # Search for chest armor that is at least item level 925 and have at least 3 affixes of the affixPool. At least 2 of the matched affixes must be greater affixes
  - NiceArmor:
      itemType: chest armor
      minPower: 925
      affixPool:
        - count:
            - { name: dexterity }
            - { name: damage_reduction }
            - { name: lucky_hit_chance }
            - { name: total_armor }
            - { name: maximum_life }
          minCount: 3
          minGreaterAffixCount: 2

  # Search for boots that have at least 2 of the specified affixes and either max evade charges or reduced evade cooldown as inherent affix
  - GreatBoots:
      itemType: boots
      minPower: 800
      inherentPool:
        - count:
            - { name: maximum_evade_charges }
            - { name: attacks_reduce_evades_cooldown_by_seconds }
          minCount: 1
      affixPool:
        - count:
            - { name: movement_speed, value: 16 }
            - { name: cold_resistance }
            - { name: lightning_resistance }
          minCount: 2

  # Search for boots with movement speed and 1 resistances from a pool of all resistances.
  # No need to add maxCount to the resistance group since it isn't possible for an item to have more than one resistance affix
  - ResBoots:
      itemType: boots
      minPower: 800
      affixPool:
        - count:
            - { name: movement_speed, value: 16 }
        - count:
            - { name: shadow_resistance }
            - { name: cold_resistance }
            - { name: lightning_resistance }
            - { name: fire_resistance }
            - { name: poison_resistance }
          minCount: 1

  # Search for boots with movement speed. At least two of all item affixes must be a greater affix
  - GreaterAffixBoots:
      itemType: boots
      minPower: 800
      minGreaterAffixCount: 2
      affixPool:
        - count:
            - { name: movement_speed, value: 16 }
```

</details>

Affix names are lower case and spaces are replaced by underscore. You can find the full list of names
in [assets/lang/enUS/affixes.json](assets/lang/enUS/affixes.json).

### AspectUpgrades (Experimental)

Legendary Aspects that you want to be notified of receiving upgrades for can be placed in your profile.
They are defined in the top-level key `AspectUpgrades`.

This filter is generally for build-specific aspects that you'd like to be made aware of when you receive an upgrade so you can
upgrade that aspect immediately at the occultist. We notify the user by favoriting the item and showing orange text or
orange highlighting when hovering over the item.

If the item matches any other profile, this filter does nothing. This filter does respect the `mark_as_favorite` config property.
Any aspects that do not match this filter or are not codex upgrades are handled by the `keep_aspects` config property.

<details><summary>Config Examples</summary>

```yaml
AspectUpgrades:
  # This would mark Snowveiled Adventurer's Pants as a favorite if it's a codex upgrade. It would ignore the pants otherwise.
  - of_singed_extremities
  - snowveiled

# This works exact same as above, it's just a different way to format it
AspectUpgrades: [of_singed_extremities, snowveiled]
```

</details>

Aspect names are lower case and spaces are replaced by underscore. You can find the full list of names
in [assets/lang/enUS/aspects.json](assets/lang/enUS/aspects.json).

### Sigils

Sigils are defined by the top-level key `Sigils`. It contains a list of affix or location names that you want to filter
for. If no Sigil filter is provided, all Sigils will be kept.

<details><summary>Config Examples</summary>

```yaml
Sigils:
  blacklist:
    # locations
    - endless_gates
    - vault_of_the_forsaken

    # affixes
    - armor_breakers
    - resistance_breakers
```

If you want to filter for a specific affix or location, you can also use the `whitelist` key. Even if `whitelist` is
present, `blacklist` will be used to discard sigils that match any of the blacklisted affixes or locations.

```yaml
# Only keep sigils for vault_of_the_forsaken without any of the affixes armor_breakers and resistance_breakers
Sigils:
  blacklist:
    - armor_breakers
    - resistance_breakers
  whitelist:
    - vault_of_the_forsaken
```

To switch that priority, you can add the `priority` key with the value `whitelist`.

```yaml
# This will keep all vault of the forsaken sigils even if they have armor_breakers or resistance_breakers
Sigils:
  blacklist:
    - armor_breakers
    - resistance_breakers
  whitelist:
    - vault_of_the_forsaken
  priority: whitelist
```

You can also create conditional filters based on a single affix or location.

```yaml
# Only keep sigils for iron_hold when it also has shadow_damage
Sigils:
  blacklist:
    - armor_breakers
    - resistance_breakers
  whitelist:
    - [ iron_hold, shadow_damage ]
```

</details>

Sigil affixes and location names are lower case and spaces are replaced by underscore. You can find the full list of
names in [assets/lang/enUS/sigils.json](assets/lang/enUS/sigils.json).

### Tributes

Tributes are defined by the top-level key `Tributes`. It contains a list of either tribute names or rarities you want
to keep. Any not in the list are not kept. If no Tribute filter is provided, all Tributes will be kept.

Mythic tributes are always kept no matter what.

<details><summary>Config Examples</summary>

```yaml
# Keeps tribute_of_mystique and all legendary and unique tributes
Tributes:
  - tribute_of_mystique
  - [legendary, unique]
```

If you're exceptionally pressed for time, you can just put the name of the tribute without "tribute_of\_" at the beginning.

```yaml
# Keeps Tribute of Mystique and Tribute of Ascendance (Resolute) and nothing else
Tributes:
  - mystique
  - ascendance_resolute
```

</details>

Tribute names are lower case and spaces are replaced by underscore. Parentheses are removed. Note that United and
Resolute identifiers are part of the names in [assets/lang/enUS/tributes.json](assets/lang/enUS/tributes.json). You can find the list of item rarities
in [rarity.py](src/item/data/rarity.py)

### Uniques

Uniques are defined by the top-level key `Uniques`. It contains a list of parameters that you want to filter for. If no
Unique filter is provided, uniques will be handled according to the handle_uniques configuration. All mythics are
marked as favorite regardless of any filter or configuration.

Uniques can be filtered in two ways. First the aspect and affix for a specific unique can be filtered directly.
This is how imported profiles are configured. If only aspect filtering is applied, then all other uniques will be
handled according to the handle_uniques property. For aspect filtering, since uniques all have a predefined affix,
you'll only need to specify the threshold that you want to apply (see examples below).

Additionally, you can filter all uniques based on a generic property like their item power or if they have greater
affixes. Once a "global" filter like this is applied then all uniques will have a filter that now applies to them
and handle_uniques will be ignored.

The following global filters are available. As a reminder, these will apply to all uniques that are not specifically
being filtered by aspect:

- `itemType`: The name of the type or a list of multiple types.
  See [assets/lang/enUS/item_types.json](assets/lang/enUS/item_types.json)
- `minGreaterAffixCount`: Only keep uniques with a specific number of greater affixes
- `minPercentOfAspect` (experimental): Only keep uniques whose aspect is above a percentage of the total possible.
  For example, if this is set to 80 and an aspect has a range of 100-200, then a value of 180 would be kept but a value
  of 150 would be marked as junk. Situations where a smaller value is what is wanted are automatically handled as well.
  This functionality is new so please report any issues found with it.
- `minPower`: The minimum item power of uniques to keep
- `mythic`: If set to true, only keep mythic uniques.

In vision mode, uniques show as <filename>.<aspect>. For example myuniques.yaml with fists_of_fate aspect defined
would show as myuniques.fists_of_fate. The label for the filename can be configured at the aspect level using the
profileAlias flag (see examples).

<details><summary>Config Examples</summary>

```yaml
# Take only mythic uniques
Uniques:
  - mythic: true
```

```yaml
# Take all uniques with item power > 900
Uniques:
  - minPower: 900
```

```yaml
# Take all uniques with at least 1 greater affix
Uniques:
  - minGreaterAffixCount: 1
```

```yaml
# Take all unique pants
Uniques:
  - itemType: pants
```

```yaml
# Take all unique chest armors and pants
Uniques:
  - itemType: [ chest armor, pants ]
```

```yaml
# Take all unique chest armors and pants with min item power > 900
Uniques:
  - itemType: [ chest armor, pants ]
    minPower: 900
```

```yaml
# Take all Tibault's Will pants
Uniques:
  - aspect: { name: tibaults_will }
```

```yaml
# Take all Tibault's Will pants with at least 2 greater affixes.
# Have vision mode show this as my_cool_items.tibaults_will instead of <filename>.tibaults_will
Uniques:
  - aspect: { name: tibaults_will }
    minGreaterAffixCount: 2
    profileAlias: my_cool_items
```

```yaml
# Take all Tibault's Will pants that have item power > 900 and dmg reduction from close > 12 as well as aspect value > 25
Uniques:
  - aspect: { name: tibaults_will, value: 25 }
    minPower: 900
    affix:
      - { name: damage_reduction_from_close_enemies, value: 12 }
```

```yaml
# Note that if a unique matches any filter, it is kept. Each - denotes a new filter.
# For example, the below will keep all uniques that have two greater affixes OR an aspect percentage greater than 80
Uniques:
  - minGreaterAffixCount: 2
  - minPercentOfAspect: 80
```

```yaml
# Conversely, this will match all uniques that have two greater affixes AND an aspect percentage greater than 80
Uniques:
  - minGreaterAffixCount: 2
    minPercentOfAspect: 80
```

</details>

Unique names are lower case and spaces are replaced by underscore. You can find the full list of names
in [assets/lang/enUS/uniques.json](assets/lang/enUS/uniques.json). Occasionally a unique is missing. If you find one missing just raise an issue and we can add it.

## Future Plans

- Evaluate bringing back the small overlay the previous versions used
- A video explaining the initial setup
- Evaluate using joystick emulation to further increase speed for users willing to do additional setup
- Finish GUI documentation
- Want something done that's not mentioned here? Leave a suggestion in the [discord](https://discord.gg/YyzaPhAN6T) or use github issues. Or, make the changes yourself and open up a PR!

## Develop

### Setup using uv

If you intend to submit PRs, create your own fork of d4lf and clone that in the steps below.

Before beginning, [install uv](https://docs.astral.sh/uv/getting-started/installation/#winget).

```bash
git clone https://github.com/d4lfteam/d4lf
cd d4lf
uv sync
python -m src.main
```

If you receive an error about missing Visual Studio code, follow the link it provides. Install Visual Studio Build Tools 2022 with the defaults selected and also select "MSVC VS 2022 C++ ..." and "Windows 11 SDK ...". Restart your terminal and try again.

### Formatting & Linting

Just use prek. If it's your first setup, run:

```bash
prek install
```

Otherwise just run:

```bash
prek run -a
```

## Credits

- Icon based of: [CarbotAnimations](https://www.youtube.com/carbotanimations/about)
- Some of the OCR code is originally from [@gleed](https://github.com/aliig). Good guy
- Names and textures for matching from [Blizzard](https://www.blizzard.com)
- Thanks to NekrosStratia for the initial idea and help with TTS mode
