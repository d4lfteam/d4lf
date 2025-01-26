import yaml
from typing import List

class Affix:
    def __init__(self, name: str):
        self.name = name

    @classmethod
    def from_dict(cls, data):
        return cls(name=data['name'])

    def to_dict(self):
        return {'name': self.name}

    def __str__(self):
        return f"name: {self.name}"


class AffixPool:
    def __init__(self, count: List[Affix], minCount: int, minGreaterAffixCount: int):
        self.count = count
        self.minCount = minCount
        self.minGreaterAffixCount = minGreaterAffixCount

    @classmethod
    def from_dict(cls, data):
        count = [Affix.from_dict(affix) for affix in data['count']]
        try:
            minCount = data['minCount']
        except KeyError:
            minCount = None
        try:
            minGreaterAffixCount = data['minGreaterAffixCount']
        except KeyError:
            minGreaterAffixCount = None
        return cls(count=count, minCount=minCount, minGreaterAffixCount=minGreaterAffixCount)

    def to_dict(self):
        if self.minCount is None or self.minGreaterAffixCount is None:
            return {
                'count': [affix.to_dict() for affix in self.count]
            }
        return {
            'count': [affix.to_dict() for affix in self.count],
            'minCount': self.minCount,
            'minGreaterAffixCount': self.minGreaterAffixCount
        }

    def __str__(self):
        return f"count: {self.count}\nminCount: {self.minCount}\nminGreaterAffixCount: {self.minGreaterAffixCount}"

    def set_count(self, newCount : List[str]):
        self.count = [ Affix(name) for name in newCount]


class Item:
    def __init__(self, itemName: str, itemType: List[str], minPower: int, affixPool: List[AffixPool], inherentPool: List[AffixPool] = None):
        self.itemName = itemName
        self.itemType = itemType
        self.minPower = minPower
        self.affixPool = affixPool
        self.inherentPool = inherentPool if inherentPool else []

    def set_affix_pool(self, newAffixPool: List[str], newMinCount : int, newGreaterCount: int):
        self.affixPool[0].minCount = newMinCount
        self.affixPool[0].minGreaterAffixCount = newGreaterCount
        self.affixPool[0].set_count(newAffixPool)

    def set_inherent_pool(self, newInherentPool: List[str]):
        self.inherentPool[0].set_count(newInherentPool)

    @classmethod
    def from_dict(cls, data):
        itemName = list(data.keys())[0]
        affixPool = [AffixPool.from_dict(pool) for pool in data[itemName]['affixPool']]
        try:
            inherentPool = [AffixPool.from_dict(pool) for pool in data[itemName]['inherentPool']]
        except:
            inherentPool = []
        try:
            minPower = data[itemName]['minPower']
        except KeyError as e:
            minPower = 0
        return cls(itemName=itemName, itemType=data[itemName]['itemType'], minPower=minPower, affixPool=affixPool, inherentPool=inherentPool)

    def to_dict(self):
        data = { f'{self.itemName}' :
            {
            'itemType': self.itemType,
            'minPower': self.minPower,
            'affixPool': [pool.to_dict() for pool in self.affixPool]
            }
        }
        if self.inherentPool:
            data[self.itemName]['inherentPool'] = [pool.to_dict() for pool in self.inherentPool]
        return data

    def __str__(self):
        affixPoolStr = f"count:\n"
        for affix in self.affixPool[0].count:
                affixPoolStr += f"\t- {affix}\n"
        affixPoolStr += f"minCount: {self.affixPool[0].minCount}\nminGreaterAffixCount: {self.affixPool[0].minGreaterAffixCount}"
        inherentPoolStr = ""
        if self.inherentPool:
            inherentPoolStr = f"count:\n"
            for inherent in self.inherentPool[0].count:
                inherentPoolStr += f"\t-{inherent}\n"
            inherentPoolStr += f"minCount: {self.inherentPool[0].minCount}\nminGreaterAffixCount: {self.inherentPool[0].minGreaterAffixCount}"
        if inherentPoolStr == "":
            return f"itemName: {self.itemName}\nitemType: {self.itemType}\nminPower: {self.minPower}\naffixPool: {affixPoolStr}\n"
        return f"itemName: {self.itemName}\nitemType: {self.itemType}\nminPower: {self.minPower}\naffixPool: {affixPoolStr}\ninherentPool: {inherentPoolStr}\n"

    def set_minPower(self, minPower):
        self.minPower = minPower

    def set_itemType(self, itemType):
        self.itemType = itemType

    def set_itemName(self, itemName):
        self.itemName = itemName

    def set_minGreaterAffix(self, minGreaterAffix):
        self.affixPool[0].minGreaterAffixCount = minGreaterAffix

class Root:
    def __init__(self, affixes: List[Item], data):
        self.affixes = affixes
        self.data = data

    @classmethod
    def from_dict(cls, data):
        affixes = [Item.from_dict(item) for item in data['Affixes']]
        return cls(affixes=affixes, data=data)

    def to_dict(self):
        self.data['Affixes'] = [item.to_dict() for item in self.affixes]
        return self.data

    def set_min_power(self, minPower):
        for affix in self.affixes:
            affix.set_minPower(minPower)

    @classmethod
    def load_yaml(cls, file_path):
        with open(file_path, 'r') as file:
            data = yaml.safe_load(file)
        return cls.from_dict(data)

    def save_yaml(self, file_path):
        with open(file_path, 'w') as file:
            yaml.safe_dump(self.to_dict(), file)