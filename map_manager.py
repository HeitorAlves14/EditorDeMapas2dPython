# map_manager.py
import os, json
from collections import defaultdict
import geometry as geo
import config
from data_structures import Sector, Entity, Wall, BSPNode, ATTRIBUTE_REGISTRY, ENTITY_ATTRIBUTE_REGISTRY

# -----------------------------
# Estado do editor (Variáveis globais do Módulo)
# -----------------------------
sectors = []
current_vertices = []
selected_sector = None
sectors_by_id = {}
children_by_parent = defaultdict(list)
portal_hint_segments = [] # pares ((a1,a2),(b1,b2)) candidatos
entities = []
selected_entity = None

def rebuild_indices():
    global sectors_by_id, children_by_parent
    sectors_by_id.clear()
    children_by_parent.clear()
    for s in sectors:
        sectors_by_id[s.id] = s
        if s.parent_id is not None:
            children_by_parent[s.parent_id].append(s)

def add_sector(sec):
    global sectors, sectors_by_id, children_by_parent
    sectors.append(sec)
    sectors_by_id[sec.id] = sec
    if sec.parent_id is not None:
        children_by_parent[sec.parent_id].append(sec)

def add_entity(pos, etype, grid_map, angle=0.0):
    """Cria uma nova entidade na posição."""
    # Posição convertida dos pixeis da tela para coordenadas de grade
    map_x, map_y = screen_to_map(pos[0], pos[1])
    map_pos = (map_x, map_y)
    # Encontra o setor em que a entidade está.
    sector_id = None
    pt = map_pos
    
    # Lógica para achar o setor (reutilizando pick_sector_recursive)
    roots = [s for s in sectors if getattr(s, "parent_id", None) is None]
    roots.sort(key=lambda s: geo.area_polygon(s.outer), reverse=True)
    for root in roots:
        sec = pick_sector_recursive(pt, root)
        if sec:
            sector_id = sec.id
            break

    e = Entity(map_pos, etype=etype, sector_id=sector_id)
    entities.append(e)
    global selected_entity
    selected_entity = e
    return f"Entidade {e.id} ({etype}) criada no setor {sector_id}."

def depth(sector):
    d = 0
    cur = sector
    while getattr(cur, "parent_id", None) is not None:
        parent = sectors_by_id.get(cur.parent_id)
        if not parent:
            break
        d += 1
        cur = parent
    return d

# -----------------------------
# Atributos dinâmicos (Shell/Getter/Setter)
# -----------------------------
# get_attr, set_attr, clear_all_attrs, remove_attrs, apply_default_attrs, copy_attrs_between_maps
# ... (mover estas funções, usando ATTRIBUTE_REGISTRY importado)

def get_registry(obj):
    """Retorna o registro de atributos apropriado (Setor ou Entidade)."""
    if isinstance(obj, Sector):
        return ATTRIBUTE_REGISTRY
    elif isinstance(obj, Entity):
        return ENTITY_ATTRIBUTE_REGISTRY
    return {} # Se não for um objeto com registro padrão, retorna vazio

def get_attr(obj, key):
    """Retorna o valor de um atributo ou seu valor padrão."""
    registry = get_registry(obj)

    # 1. Tentar obter o valor diretamente
    if key in obj.attrs:
        return obj.attrs[key]

    # 2. Se não estiver armazenado, buscar o valor padrão no registro (se existir)
    if key in registry:
        return registry[key].default

    # 3. Retornar None se não for encontrado
    return None

def set_attr(obj, key, value):
    """Tenta definir um atributo para um Setor ou Entidade, com validação de tipo."""
    registry = get_registry(obj)
    
    # 1. Tentar validar contra o registro padrão
    if key in registry:
        spec = registry[key]
        try:
            # Tenta converter o valor (que vem como string) para o tipo correto
            converted_value = spec.typ(value)
            obj.attrs[key] = converted_value
            return True
        except (ValueError, TypeError):
            return False # Falha na conversão
    
    # 2. Se a chave não está no registro (atributo customizado ou de parede):
    # Armazena como string
    obj.attrs[key] = str(value) 
    return True



def screen_to_map(sx, sy):
    return ((sx - config.CAM_OFFSET_X) / config.GRID,
            (sy - config.CAM_OFFSET_Y) / config.GRID)

def remove_attrs(obj, keys):
    """Remove atributos customizados de um setor ou entidade."""
    for key in keys:
        if key in obj.attrs:
            del obj.attrs[key]
# ... (outras funções de atributo)

# -----------------------------
# Interações essenciais (Desenho/Seleção)
# -----------------------------

def add_vertex(mx, my, grid, use_snap):
    global current_vertices
    if use_snap:
        nx, ny = geo.snap_to_grid(mx - config.CAM_OFFSET_X, my - config.CAM_OFFSET_Y, grid)
    else:
        nx, ny = mx - config.CAM_OFFSET_X, my - config.CAM_OFFSET_Y
    
    map_x = nx / grid
    map_y = ny / grid

    current_vertices.append((map_x, map_y))

def close_sector():
    global current_vertices, sectors, selected_sector
    if len(current_vertices) < 3:
        return "Setor precisa de 3+ vértices."
    if not geo.is_convex_polygon(current_vertices):
        return "Setor não é convexo."
    if geo.area_polygon(current_vertices) < 0:
        current_vertices = list(reversed(current_vertices))

    parents = [s for s in sectors
               if geo.point_in_poly(current_vertices[0], s.outer)
               and not geo.polys_intersect(current_vertices, s.outer)
               and all(geo.point_in_poly(v, s.outer) for v in current_vertices)]

    if parents:
        parent_id = min(parents, key=lambda s: abs(geo.area_polygon(s.outer))).id
    else:
        parent_id = None

    s = Sector(current_vertices, parent_id=parent_id)
    add_sector(s)
    current_vertices = []
    message = f"Setor {s.id} criado." if parent_id is None else f"Cômodo {s.id} dentro do setor {parent_id}."
    rebuild_indices()
    return message

def pick_sector_recursive(pt, sector):
    if not geo.point_in_poly(pt, sector.outer):
        return None
    children = children_by_parent.get(sector.id, [])
    for child in sorted(children, key=lambda c: abs(geo.area_polygon(c.outer))):
        found = pick_sector_recursive(pt, child)
        if found:
            return found
    return sector

def pick_sector(mx, my, grid_map):
    global selected_sector

    mx, my, = geo.snap_to_grid(mx, my, grid_map)
    
    map_x, map_y = screen_to_map(mx, my)
    pt = (map_x, map_y)

    roots = [s for s in sectors if getattr(s, "parent_id", None) is None]
    roots.sort(key=lambda s: abs(geo.area_polygon(s.outer)), reverse=True)
    for root in roots:
        found = pick_sector_recursive(pt, root)
        if found:
            selected_sector = found
            return f"Selecionado setor {selected_sector.id}"
    selected_sector = None
    return "Nenhum setor sob o clique."

def pick_entity(mx, my, grid_map):
    """Tenta selecionar uma entidade próxima ao clique."""
    global selected_entity
    map_x, map_y = screen_to_map(mx, my)
    pt = (map_x, map_y)
    
    # Itera sobre entidades de trás para frente (última criada é a mais visível)
    for entity in reversed(entities):
        e_pos = entity.pos
        if geo.point_distance(pt, e_pos) < config.TOLERANCE:
            selected_entity = entity
            return f"Entidade {selected_entity.id} ({selected_entity.type}) selecionada."
            
    selected_entity = None
    return "Nenhuma entidade selecionada."

def remove_entity(entity):
    """Remove uma entidade do mapa."""
    if entity in entities:
        entities.remove(entity)
        global selected_entity
        if selected_entity == entity:
            selected_entity = None
        return f"Entidade {entity.id} removida."
    return "Entidade não encontrada."

# -----------------------------
# Persistência
# -----------------------------
# export_map, load_map, clear_map

# -----------------------------
# Walls e BSP
# -----------------------------

def build_walls(sectors_):
    edge_map = defaultdict(list)
    for s in sectors_:
        if len(s.outer) < 2: continue
        for a, b in geo.edges_of(s.outer):
            key = geo.normalize_edge(a, b)
            edge_map[key].append(s.id)

    walls = []
    for s in sectors_:
        if len(s.outer) < 2: continue
        for i, (a, b) in enumerate(geo.edges_of(s.outer)):
            rev_key = geo.normalize_edge(b, a)
            back_ids = [sid2 for sid2 in edge_map.get(rev_key, []) if sid2 != s.id]
            back_id = back_ids[0] if back_ids else None
            
            is_portal = False
            if get_attr(s, f"wall_{i}") == "portal" and back_id is not None:
                is_portal = True
            walls.append(Wall(a, b, s.id, back_id, is_portal=is_portal))
    return walls

def choose_splitter(segments):
    best_score = float("inf")
    best_splitter = None

    for candidate in segments:
        rest = [s for s in segments if s is not candidate]
        front, back, collinear = geo.split_segments(rest, candidate)

        cuts = len(front) + len(back) - len(rest)
        balance = abs(len(front) - len(back))
        score = cuts * 5 + balance

        if score < best_score:
            best_score = score
            best_splitter = candidate
    return best_splitter

def build_bsp_from_walls(walls):
    segs = [ (w.start, w.end) for w in walls ]
    if not segs: return None
    def build(segments):
        if not segments: return None
        if geo.all_collinear(segments):
            return BSPNode(segments[0], collinear=segments)
        if len(segments) == 1:
            return BSPNode(segments[0], collinear=[])
        
        splitter = choose_splitter(segments)
        rest = [s for s in segments if s is not splitter]

        front, back, collinear = geo.split_segments(rest, splitter)

        if not front and not back:
            return BSPNode(splitter, collinear=collinear)

        front = [s for s in front if geo.segment_length(s) > 1]
        back  = [s for s in back if geo.segment_length(s) > 1]
        
        node = BSPNode(splitter, collinear=collinear)
        node.front_segments = front
        node.back_segments = back

        node.front = build(front)
        node.back = build(back)
        return node
    
    return build(segs)

# -----------------------------
# Portal assist (visual + persistência)
# -----------------------------
# compute_portal_hints, try_create_portal_at_point

def compute_portal_hints():
    global portal_hint_segments
    portal_hint_segments = []
    valid_loops = [(s, s.outer) for s in sectors if len(s.outer) >= 2]
    for i in range(len(valid_loops)):
        s1, l1 = valid_loops[i]
        for j in range(i+1, len(valid_loops)):
            s2, l2 = valid_loops[j]
            if s1.id == s2.id: continue
            for a1,a2 in geo.edges_of(l1):
                for b1,b2 in geo.edges_of(l2):
                    if geo.almost_colinear(a1,a2,b1,b2) and geo.overlap_on_line(a1,a2,b1,b2):
                        portal_hint_segments.append(((a1,a2),(b1,b2)))

def try_create_portal_at_point(pt, grid_map):
    # Converte pixels da tela para espaçamento da grade
    nx, ny = geo.snap_to_grid(pt[0], pt[1], grid_map)
    pt = (nx / grid_map, ny / grid_map)

    created = False
    for (a1,a2),(b1,b2) in portal_hint_segments:
        if geo.point_line_distance(pt, a1, a2) < config.TOLERANCE or geo.point_line_distance(pt, b1, b2) < config.TOLERANCE:
            for s in sectors:
                for i,(v1,v2) in enumerate(geo.edges_of(s.outer)):
                    if geo.almost_colinear(a1,a2,v1,v2) and geo.overlap_on_line(a1,a2,v1,v2):
                        current = get_attr(s, f"wall_{i}")
                        if current == "portal":
                            remove_attrs(s, [f"wall_{i}"])
                        else:
                            set_attr(s, f"wall_{i}", "portal")
                        created = True
    return created

# Funções de I/O (Exportar/Importar)
def export_map(map_name="map.json"):

    #1- Cria o diretório (se não existir)
    os.makedirs(map_name, exist_ok=True)

    #2- Prepara os dados do mapa (Setores e Paredes)
    walls = build_walls(sectors)
    map_data = {
        "sectors": [s.to_json() for s in sectors],
        "walls": [w.to_json() for w in walls],
    }

    #3- Prepara os dados das entidades
    entity_data = {
        "entities": [e.to_json() for e in entities],
    }

    #4- Exportar map.json
    map_filepath = os.path.join(map_name, "map.json")
    with open(map_filepath, "w", encoding="utf-8") as f:
        json.dump(map_data, f, indent=2)
    
    entities_filepath = os.path.join(map_name, "entities.json")
    with open(entities_filepath, "w", encoding="utf-8") as f:
        json.dump(entity_data, f, indent=2)
    return f"Mapa '{map_name}' exportado com sucesso em 2 arquivos: map.json e entities.json."

def load_map(map_name="map.json"):
    # Carrega o mapa da estrutura de pasta
    global sectors, entities, current_vertices, selected_sector, selected_entity

    map_filepath = os.path.join(map_name, "map.json")
    entities_filepath = os.path.join(map_name, "entities.json")

    if not os.path.exists(map_filepath):
        return f"ERRO: Arquivo de mapa não encontrado, verifique se o nome está certo."

    #1 Carrega mapa com setores e paredes.
    sectors.clear()
    with open(map_filepath, "r", encoding="utf-8") as f:
        map_data = json.load(f)

    #sectors = []
    for sdata in map_data.get("sectors", []):
        outer = [tuple(v) for v in sdata["outer"]]
        sec = Sector(outer, parent_id=sdata.get("parent_id"), attrs=sdata.get("attrs", {}))
        sec.id = sdata["id"]

        for key, spec in ATTRIBUTE_REGISTRY.items():
            if key not in sec.attrs:
                sec.attrs[key] = spec.default

        sectors.append(sec)

    # Carrega entidades do mapa.
    entities.clear()
    if os.path.exists(entities_filepath):
        with open(entities_filepath, "r", encoding="utf-8") as f:
            entity_data = json.load(f)
        
        for edata in entity_data.get("entities", []):
            pos = tuple(edata["pos"])
            ent = Entity(pos,
                         etype=edata.get("type", "generic"),
                         angle=edata.get("angle", 0.0),
                         sector_id=edata.get("sector_id")
                         )
            ent.id = edata["id"]
            ent.attrs.update(edata.get("attrs", {}))

            for key, spec in ENTITY_ATTRIBUTE_REGISTRY.items():
                if key not in ent.attrs:
                    ent.attrs[key] = spec.default

            entities.append(ent)
    else:
        # Aviso para o usuário se o arquivo secundário estiver faltando
        print(f"Aviso: Arquivo de entidades {entities_filepath} não encontrado. Assumindo zero entidades.")

    max_sector_id = max((s.id for s in sectors), default=0)
    Sector.set_next_id(max_sector_id + 1)

    max_entity_id = max((e.id for e in entities), default=0)
    Entity.set_next_id(max_entity_id + 1)

    rebuild_indices()

    selected_sector = None
    selected_entity = None
    current_vertices = []

    return f"Mapa '{map_name}' carregado. Setores: {len(sectors)}. Entidades: {len(entities)}."

def clear_map():
    global sectors, current_vertices, selected_sector
    sectors = []
    Sector.set_next_id(1)
    Entity.set_next_id(1)
    rebuild_indices()
    selected_sector = None
    current_vertices = []
    return "Mapa limpo. Pronto para começar um novo!"