# ui.py
import pygame as pg
import config
import map_manager as mm
from data_structures import ATTRIBUTE_REGISTRY, ENTITY_ATTRIBUTE_REGISTRY, WALL_ATTRIBUTE_REGISTRY

# Variáveis globais de UI (Estado de UI)
font = None
ui_elements = []
attr_elements = []
help_elements = []
message = "Bem-vindo ao Editor de Mapas."
mode = "draw"
show_grid = True
use_snap = True
show_bsp = False

def init_ui(pg_font, on_export_func=None, on_load_func=None, on_clear_func=None, on_bsp_toggle_func=None):
    """Inicializa fontes e constrói a UI inicial."""
    global font
    font = pg_font

class UIButton:
    def __init__(self, rect, text, action):
        self.rect = rect
        self.text = text
        self.action = action
        self.color = config.COL_SECTOR
        self.text_color = config.COL_TEXT

    def draw(self, screen):
        pg.draw.rect(screen, self.color, self.rect)
        text_surf = font.render(self.text, True, self.text_color)
        screen.blit(text_surf, (self.rect.x + 5, self.rect.y + 5))

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.action()
                return True
        return False

# --- UI Builders ---
def rebuild_ui(on_export_func, on_load_func, on_clear_func, on_bsp_toggle_func):
    """Reconstrói os botões fixos da UI."""
    global ui_elements, attr_elements, help_elements
    ui_elements.clear()
    
    # Botões de controle de mapa
    y = 10
    ui_elements.append(UIButton(pg.Rect(config.VIEW_W + 10, y, config.UI_W - 20, 30), "Exportar [E]", on_export_func))
    y += 40
    ui_elements.append(UIButton(pg.Rect(config.VIEW_W + 10, y, config.UI_W - 20, 30), "Carregar", on_load_func))
    y += 40
    ui_elements.append(UIButton(pg.Rect(config.VIEW_W + 10, y, config.UI_W - 20, 30), "Novo Mapa", on_clear_func))
    y += 40
    ui_elements.append(UIButton(pg.Rect(config.VIEW_W + 10, y, config.UI_W - 20, 30), "Toggle BSP [B]", on_bsp_toggle_func))
    y += 40
    
    # Atualiza a seção de atributos (abaixo)
    rebuild_attr_panel()
    rebuild_help_panel()

def rebuild_attr_panel():
    """Cria os elementos de UI para os atributos do setor selecionado."""
    global attr_elements
    attr_elements.clear()
    
    # Atributos dinâmicos são apenas strings na UI por simplicidade
    y_start = 220
    if mm.selected_entity:
        entity = mm.selected_entity
        
        # ... (Exibição básica de ID, tipo, posição, etc.) ...
        attr_elements.append((y_start, f"ENTIDADE {entity.id} | Tipo: {entity.type}", config.COL_PORTAL_CONFIRMED))
        y_start += 20
        attr_elements.append((y_start, f"Pos: {entity.pos[0]:.0f}, {entity.pos[1]:.0f} | Ang: {entity.angle:.0f}", config.COL_TEXT))
        y_start += 20
        attr_elements.append((y_start, f"Setor ID: {entity.sector_id}", config.COL_TEXT))
        y_start += 20
        
        # 1. Atributos Padrão
        y_start += 10
        attr_elements.append((y_start, "--- Atributos Padrão (A) ---", config.COL_TEXT))
        y_start += 20
        
        for key, spec in ENTITY_ATTRIBUTE_REGISTRY.items():
            val = mm.get_attr(entity, key) # Usa o get_attr unificado
            
            # Formatação para destacar se o valor foi alterado do padrão
            if val is not None and val != spec.default:
                display_val = str(val)
                color = config.COL_SECTOR_SELECTED # Destaca valores alterados
            else:
                display_val = f"(Padrão: {spec.default})"
                color = config.COL_TEXT
            
            attr_elements.append((y_start, f"{key}: {display_val}", color))
            y_start += 20
        
        # 2. Atributos Customizados (para exibir atributos que NÃO SÃO padrão)
        y_start += 10
        attr_elements.append((y_start, "--- Atributos Customizados ---", config.COL_TEXT))
        y_start += 20
        
        for key, val in entity.attrs.items():
            if key not in ENTITY_ATTRIBUTE_REGISTRY: # Apenas mostra os customizados
                attr_elements.append((y_start, f"{key}: {val}", config.COL_SECTOR))
                y_start += 20
        
        y_start += 10
        # Continua para a seção de setores, mas com y_start mais alto

    elif mm.selected_sector:
        for sec in mm.selected_sector:
            # --- Título e Atributos do Setor ---
            attr_elements.append((y_start, f"Setor {sec.id} | Prof: {mm.depth(sec)}", config.COL_SECTOR_SELECTED))
            y_start += 20
            
            for key, spec in ATTRIBUTE_REGISTRY.items():
                val = mm.get_attr(sec, key)
                color = config.COL_SECTOR if key in sec.attrs else config.COL_TEXT
                display_val = str(val) if key in sec.attrs else f"(Padrão: {spec.default})"
                attr_elements.append((y_start, f"  {key}: {display_val}", color))
                y_start += 20
            
            # --- Atributos de Parede ---
            y_start += 10
            attr_elements.append((y_start, "--- Paredes ---", config.COL_SECTOR_SELECTED))
            y_start += 20

            for i in range(len(sec.outer)):
                attr_elements.append((y_start, f"wall_{i}:", config.COL_WARN))
                y_start += 20
                
                # Lista os atributos padrões da parede
                for key, spec in WALL_ATTRIBUTE_REGISTRY.items():
                    val = mm.get_attr(sec, key, wall_idx=i)
                    actual_key = f"wall_{i}_{key}"
                    
                    color = config.COL_TEXT
                    display_val = f"(Padrão: {spec.default})"
                    
                    # Se o atributo foi customizado:
                    if actual_key in sec.attrs:
                        display_val = str(val)
                        color = config.COL_PORTAL_CONFIRMED if key == "type" and val == "portal" else config.COL_SECTOR_SELECTED
                        
                    attr_elements.append((y_start, f"  {key}: {display_val}", color))
                    y_start += 20

def rebuild_help_panel():
    """Cria a lista de comandos de ajuda."""
    global help_elements
    help_elements.clear()
    
    y_start = config.H - 180
    help_elements.append((y_start, "--- Comandos ---", config.COL_TEXT))
    y_start += 20
    
    # Comandos
    help_elements.append((y_start, f"[Mudar Modo [TAB]]: {mode.upper()}", config.COL_TEXT))
    y_start += 20
    help_elements.append((y_start, f"[Grid [G]]: {'ON' if show_grid else 'OFF'}", config.COL_TEXT))
    y_start += 20
    help_elements.append((y_start, f"[Snap [S]]: {'ON' if use_snap else 'OFF'}", config.COL_TEXT))
    y_start += 20
    help_elements.append((y_start, "[Limpar Vértices [N]]", config.COL_TEXT))
    y_start += 20
    help_elements.append((y_start, "[Desfazer Vértice [Z]]", config.COL_TEXT))
    y_start += 20
    help_elements.append((y_start, "[Atribuir Attr [A]]", config.COL_TEXT))
    y_start += 20
    help_elements.append((y_start, "[Deletar Setor [DEL]]", config.COL_TEXT))
    y_start += 20
    help_elements.append((y_start, "[Wall Attr [W]]", config.COL_TEXT))


# --- Drawing ---
def draw_ui(screen):
    """Desenha todos os elementos da UI (painel lateral)."""
    
    # Fundo da UI
    ui_rect = pg.Rect(config.VIEW_W, 0, config.UI_W, config.H)
    pg.draw.rect(screen, config.COL_UI, ui_rect)
    
    # Linha divisória
    pg.draw.line(screen, config.COL_TEXT, (config.VIEW_W, 0), (config.VIEW_W, config.H), 1)

    # Modo Atual
    mode_text = font.render(f"MODO: {mode.upper()}", True, config.COL_SECTOR_SELECTED)
    screen.blit(mode_text, (config.VIEW_W + 10, 180))

    # Mensagem de status
    message_text = font.render(message, True, config.COL_WARN)
    screen.blit(message_text, (config.VIEW_W + 10, 200))

    # Botões
    for element in ui_elements:
        element.draw(screen)

    # Painel de Atributos
    for y, text, color in attr_elements:
        text_surf = font.render(text, True, color)
        screen.blit(text_surf, (config.VIEW_W + 10, y))

    # Painel de Ajuda/Comandos
    for y, text, color in help_elements:
        text_surf = font.render(text, True, color)
        screen.blit(text_surf, (config.VIEW_W + 10, y))

def handle_ui_event(event):
    """Trata eventos para botões de UI."""
    for element in ui_elements:
        if element.handle_event(event):
            return True
    return False

# --- Status Functions ---
def set_message(new_message):
    global message
    message = new_message

def set_mode(new_mode):
    global mode
    mode = new_mode
    rebuild_help_panel() # Atualiza o texto do modo no painel de ajuda

def toggle_grid():
    global show_grid
    show_grid = not show_grid

def toggle_snap():
    global use_snap
    use_snap = not use_snap

def toggle_bsp():
    global show_bsp
    show_bsp = not show_bsp
