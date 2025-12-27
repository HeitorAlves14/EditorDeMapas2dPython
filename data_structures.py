# data_structures.py
import json
from collections import defaultdict
from geometry import area_polygon # Importação relativa após a separação

# -----------------------------
# Atributos dinâmicos
# -----------------------------
class AttributeSpec:
    def __init__(self, key, typ, default):
        self.key = key
        self.typ = typ
        self.default = default

# Registro padrão dos setores
ATTRIBUTE_REGISTRY = {}

# Aqui adiciona os atributos padrões
ATTRIBUTE_REGISTRY["floor_text"] = AttributeSpec("floor_text", int, None)
ATTRIBUTE_REGISTRY["ceiling_text"] = AttributeSpec("ceiling_text", int, None)
ATTRIBUTE_REGISTRY["wall_text"] = AttributeSpec("wall_text", int, None)
ATTRIBUTE_REGISTRY["floor_h"] = AttributeSpec("floor_h", float, 0.0)
ATTRIBUTE_REGISTRY["ceiling_h"] = AttributeSpec("ceiling_h", float, 4.0)

ATTRIBUTE_REGISTRY["light_level"] = AttributeSpec("light_level", int, 255)
ATTRIBUTE_REGISTRY["is_sky"] = AttributeSpec("is_sky", bool, False)
ATTRIBUTE_REGISTRY["special"] = AttributeSpec("special", str, "")
ATTRIBUTE_REGISTRY["damage"] = AttributeSpec("damage", int, 0)
ATTRIBUTE_REGISTRY["is_secret"] = AttributeSpec("is_secret", bool, False)

ATTRIBUTE_REGISTRY["floor_off"] = AttributeSpec("floor_off", int, 8)
ATTRIBUTE_REGISTRY["ceiling_off"] = AttributeSpec("ceiling_off", int, 16)
ATTRIBUTE_REGISTRY["wall_off"] = AttributeSpec("wall_off", int, 32)

# Registros padrão das entidades.
ENTITY_ATTRIBUTE_REGISTRY = {}

ENTITY_ATTRIBUTE_REGISTRY["skill_level"] = AttributeSpec("skill_level", int, None)
ENTITY_ATTRIBUTE_REGISTRY["is_enemy"] = AttributeSpec("is_enemy", bool, True)

# -----------------------------
# Dados do editor (classes)
# -----------------------------
class Sector:
    _next_id = 1
    def __init__(self, outer_vertices, parent_id=None, attrs=None):
        self.id = Sector._next_id
        Sector._next_id += 1
        self.outer = outer_vertices[:]
        self.parent_id = parent_id
        self.attrs = {}
        if attrs:
            self.attrs.update(attrs)

    def to_json(self):
        attrs_output = {}
        for key, spec in ATTRIBUTE_REGISTRY.items():
            # Obtém o valor de self.attrs ou o valor padrão (spec.default).
            val = self.attrs.get(key, spec.default)
            attrs_output[key] = val
            
        return {
            "id": self.id,
            "outer": [[round(x,2), round(y,2)] for (x,y) in self.outer],
            "parent_id": self.parent_id,
            "attrs": attrs_output
        }

    def __repr__(self):
        return f"<Sector id={self.id}, verts={len(self.outer)}, parent={self.parent_id}, attrs={self.attrs}> "
    
    @classmethod
    def set_next_id(cls, next_id):
        cls._next_id = next_id


class Entity:
    # A classe Entity e seus métodos...
    _next_id = 1
    ICONS = {
        "player_spawn": (0, 255, 0),
        "enemy": (255, 0, 0),
        "barrel": (150, 75, 0),
        "pickup": (0, 0, 255),
    }

    def __init__(self, pos, etype="generic", angle=0.0, sector_id=None, attrs=None):
        self.id = Entity._next_id
        Entity._next_id += 1
        self.type = etype
        self.pos = tuple(pos)
        self.angle = angle
        self.sector_id = sector_id
        self.attrs = attrs or {}

    def to_json(self):
        # Combina atributos modificados com valores padrão das entidades.
        attrs_output = {}
        # ...

        # Corrigido self.etype para self.type em ambas as ocorrências:
        entity_type_attrs = ENTITY_ATTRIBUTE_REGISTRY
        # A linha acima pode ser simplificada, pois o registro é global.
        
        # Iterar sobre todos os atributos definidos para este tipo de entidade
        for key, spec in entity_type_attrs.items(): # Uso direto do registro global
            # Obtém o valor de self.attrs ou o valor padrão do registro.
            val = self.attrs.get(key, spec.default)
            attrs_output[key] = val

        return {
            "id": self.id,
            # Corrigido: self.etype -> self.type
            "type": self.type, 
            "pos": [round(self.pos[0], 2), round(self.pos[1], 2)],
            "angle": round(self.angle, 3),
            "sector_id": self.sector_id,
            "attrs": attrs_output
        }
    
    @classmethod
    def set_next_id(cls, next_id):
        cls._next_id = next_id

class Wall:
    # A classe Wall...
    def __init__(self, start, end, front_id, back_id, is_portal=False):
        self.start = start
        self.end = end
        self.sector_front = front_id
        self.sector_back = back_id
        self.is_portal = is_portal

    def to_json(self):
        return {
            "start": [round(self.start[0],2), round(self.start[1],2)],
            "end": [round(self.end[0],2), round(self.end[1],2)],
            "sector_front": self.sector_front,
            "sector_back": self.sector_back,
            "is_portal": self.is_portal
        }

class BSPNode:
    # A classe BSPNode...
    def __init__(self, line, front=None, back=None, collinear=None):
        self.line = line
        self.front = front
        self.back = back
        self.collinear = collinear or []
        self.front_segments = []
        self.back_segments = []

    def to_json(self):
        return {
            "line": [[round(self.line[0][0],2), round(self.line[0][1],2)],
                     [round(self.line[1][0],2), round(self.line[1][1],2)]],
            "front": self.front.to_json() if isinstance(self.front, BSPNode) else None,
            "back": self.back.to_json() if isinstance(self.back, BSPNode) else None
        }