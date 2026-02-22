# map_manager.py
import os, json
from collections import defaultdict
import geometry as geo
import config
from data_structures import Sector, Entity, Wall, BSPNode, ATTRIBUTE_REGISTRY, ENTITY_ATTRIBUTE_REGISTRY, WALL_ATTRIBUTE_REGISTRY
import datetime

# -----------------------------
# Estado do editor (Variáveis globais do Módulo)
# -----------------------------
sectors = []
current_vertices = []
selected_sector = []
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
# Atributos dinâmicos (Getter/Setter)
# -----------------------------

def get_registry(obj, is_wall=False):
    """Retorna o registro de atributos apropriado (Setor ou Entidade)."""
    if is_wall: return WALL_ATTRIBUTE_REGISTRY
    elif isinstance(obj, Sector): return ATTRIBUTE_REGISTRY
    elif isinstance(obj, Entity): return ENTITY_ATTRIBUTE_REGISTRY
    return {} # Se não for um objeto com registro padrão, retorna vazio

def get_attr(obj, key, wall_idx=None):
    """Retorna o valor de um atributo ou seu valor padrão."""
    registry = get_registry(obj, is_wall=(wall_idx is not None))

    # Se for parede, a chave real no dicionário do setor tem prefixo
    actual_key = f"wall_{wall_idx}_{key}" if wall_idx is not None else key

    if actual_key in obj.attrs:
        return obj.attrs[actual_key]
    
    if key in registry:
        return registry[key].default
    
    return None

def set_attr(obj, key, value, wall_idx=None):
    """Tenta definir um atributo para um Setor ou Entidade, com validação de tipo."""
    registry = get_registry(obj, is_wall=(wall_idx is not None))
    actual_key = f"wall_{wall_idx}_{key}" if wall_idx is not None else key
    
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
    else: # Armazena como string
        obj.attrs[key] = str(value) 

    # Se editamos uma parede que é portal, precisamos sincronizar o outro lado
    if wall_idx is not None and key == "type" and isinstance(obj, Sector):
        opp = find_opposite_wall(obj, wall_idx)
        if opp:
            s2, j = opp
            other_key = f"wall_{j}_{key}"
            if s2.attrs.get(other_key) != obj.attrs[actual_key]:
                s2.attrs[other_key] = obj.attrs[actual_key]

    return True



def screen_to_map (mx, my):
    """Converte coordenadas da tela para coordenadas do mapa."""
    return (
        (mx - config.CAM_OFFSET_X)/config.GRID,
        (my - config.CAM_OFFSET_Y)/config.GRID
    )

def map_tolerance_pixels(px=6):
    return (px- config.CAM_OFFSET_X)/config.GRID

def remove_attrs(obj, keys, wall_idx=None):
    """Remove atributos customizados de um setor ou entidade."""
    for key in keys:
        actual_key = f"wall_{wall_idx}_{key}" if wall_idx is not None else key
        if actual_key in obj.attrs:
            del obj.attrs[actual_key]

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

def pick_sector(mx, my, grid_map, add=False):
    global selected_sector

    pt = screen_to_map(mx, my)

    roots = [s for s in sectors if s.parent_id is None]
    roots.sort(key=lambda s: abs(geo.area_polygon(s.outer)), reverse=True)

    for root in roots:
        found = pick_sector_recursive(pt, root)
        if found:
            if add:
                if found not in selected_sector:
                    selected_sector.append(found)
            else:
                selected_sector = [found]
            return f"Selecionado setor {found.id}"
    if not add:
        selected_sector = []
    return "Nenhum setor sob o clique."

def pick_entity(mx, my, grid_map):
    """Tenta selecionar uma entidade próxima ao clique."""
    global selected_entity
    map_x, map_y = screen_to_map(mx, my)
    pt = (map_x, map_y)
    
    # Itera sobre entidades de trás para frente (última criada é a mais visível)
    for entity in reversed(entities):
        e_pos = entity.pos
        tol = map_tolerance_pixels(8)
        if geo.point_distance(pt, e_pos) < tol:
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

def pick_wall(screen_pt, px_tol=15):
    # Converte o clique da tela para coordenadas do mapa (onde as paredes vivem)
    pt = screen_to_map(*screen_pt)
    
    # A tolerância no mundo do mapa deve ser proporcional ao GRID
    # Se o grid é 20, uma tolerância de 5 unidades de mapa é boa
    world_tol = px_tol / (config.GRID / 10 if config.GRID > 0 else 1)

    best_wall = None
    min_dist = world_tol

    for s in sectors:
        for i, (v1, v2) in enumerate(geo.edges_of(s.outer)):
            dist = geo.point_line_distance(pt, v1, v2)
            if dist < min_dist:
                min_dist = dist
                best_wall = (s, i, v1, v2)
                
    return best_wall

def find_opposite_wall(sector, wall_index):
    a, b = sector.outer[wall_index], sector.outer[(wall_index+1) % len(sector.outer)]

    for s2 in sectors:
        if s2 is sector:
            continue
        for j, (c, d) in enumerate(geo.edges_of(s2.outer)):
            if geo.same_segment(a, b, c, d):
                return s2, j

    return None

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
            
            wall_key = f"wall_{i}"
            wall_attr = s.attrs.get(wall_key, None)
            is_portal = False
            if get_attr(s, "type", wall_idx=i) == "portal":
                is_portal = True
            walls.append(Wall(a, b, s.id, back_id, is_portal=is_portal, attrs={"tag": wall_attr}))
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

def try_create_portal_at_point(screen_pt, grid_map):
    picked = pick_wall(screen_pt)
    if not picked: return False

    s, i, a, b = picked
    opposite = find_opposite_wall(s, i)

    if not opposite: return False  # parede externa, não pode ser portal

    s2, j = opposite

    if get_attr(s, "type", wall_idx=i) == "portal":
        remove_attrs(s, ["type"], wall_idx=i)
        remove_attrs(s2, ["type"], wall_idx=j)
    else:
        set_attr(s, "type", "portal", wall_idx=i)
        set_attr(s2, "type", "portal", wall_idx=j)
    return True

# Funções de I/O (Exportar/Importar)
def export_map(map_name="map.json", meta=None):
    #1- Cria o diretório (se não existir)
    os.makedirs(map_name, exist_ok=True)

    #2- Metadados básicos
    if meta is None:
        meta = {
            "name": map_name,
            "author": "Desconhecido",
            "version": "default.ogg",
            "created_at": datetime.datetime.now().isoformat()
        }

    map_data = {
        "meta": meta,
        "sectors": [s.to_json() for s in sectors],
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
    with open(map_filepath, "r", encoding="utf-8") as f:
        map_data = json.load(f)
    
    # --- Metadados ---
    meta = map_data.get("meta", {})
    nome = meta.get("name", "Sem nome")
    soundtrack = meta.get("soundtrack", "default.ogg")
    autor = meta.get("author", "Desconhecido")
    versao = meta.get("version", "1.0")

    sectors.clear()

    for sdata in map_data.get("sectors", []):
        outer = [tuple(v) for v in sdata["outer"]]
        sec = Sector(outer, parent_id=sdata.get("parent_id"), attrs=sdata.get("attrs", {}))
        sec.id = sdata["id"]

        # Reconstruir atributos das paredes
        for wdata in sdata.get("walls", []):
            i = wdata["index"]
            for k, v in wdata.get("attrs", {}).items():
                sec.attrs[f"wall_{i}_{k}"] = v
        
        sectors.append(sec)
    
    rebuild_indices()
    
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
    compute_portal_hints()

    selected_sector = []
    selected_entity = None
    current_vertices = []

    return f"Mapa '{map_name}' carregado. Setores: {len(sectors)}. Entidades: {len(entities)}."

def clear_map():
    global sectors, current_vertices, selected_sector
    sectors = []
    Sector.set_next_id(1)
    Entity.set_next_id(1)
    rebuild_indices()
    selected_sector = []
    current_vertices = []
    return "Mapa limpo. Pronto para começar um novo!"