# main_editor.py
import sys
import pygame as pg
import pygame_gui

# Importar os módulos
import config
import geometry as geo
import ui
import render

from map_manager import EditorContext
from TextInputBox import TextInputBox
from modes import DrawMode, SelectMode, PortalMode, EntityMode


# -----------------------------
# Inicialização
# -----------------------------
pg.init()
info = pg.display.Info()
'''config.W = info.current_w
config.H = info.current_h''' # Coloquei isso daqui só para testes
screen = pg.display.set_mode((config.W, config.H), vsync=1)
manager = pygame_gui.UIManager((config.W, config.H), 'theme.json')
pg.display.set_caption("2D Map Editor")
clock = pg.time.Clock()

try:
    font = pg.font.SysFont('Consolas', 18)
except:
    font = pg.font.Font(None, 24) # Fallback

context = EditorContext()

tools = {
    "draw": DrawMode(),
    "select": SelectMode(),
    "portal": PortalMode(),
    "entity": EntityMode()
}
current_tool_name = "draw"
current_tool = tools[current_tool_name]

ui.init_ui(font)

input_box = TextInputBox(config.VIEW_W // 2 - 150, config.H - 60, 300, 40, font)
input_purpose = None  # Pode ser "export", "load", "attr", ou "wall_attr"
input_target = None   # Guarda o objeto alvo (ex: o setor específico e a parede)

# -----------------------------
# Funções de Ação (Callbacks)
# -----------------------------

def on_export():
    global input_purpose
    ui.set_mode("typing")
    input_purpose = "export"
    input_box.activate("Nome da pasta para exportar: ")


def on_load():
    global input_purpose
    ui.set_mode("typing")
    input_purpose = "load"
    input_box.activate("Nome da pasta para carregar: ")

def on_clear():
    msg = context.clear_map()
    ui.set_message(msg)
    ui.rebuild_attr_panel()

def toggle_bsp():
    ui.toggle_bsp()
    ui.rebuild_ui(on_export, on_load, on_clear, toggle_bsp) # Atualiza o botão

# Reconstruir UI com as novas funções de callback
ui.rebuild_ui(on_export, on_load, on_clear, toggle_bsp)

def handle_entity_creation(grid_map):
    """Inicia a criação de entidade pedindo o tipo via TextInputBox."""
    global input_purpose, input_target
    ui.set_mode("typing")
    input_purpose = "entity"
    input_target = grid_map
    input_box.activate("Tipo da entidade (ex: skill_level, is_enemy): ")

def apply_attribute_from_text(input_string, target_objs, wall_idx=None):
    """
    Recebe a string da caixa de texto (ex: 'light_level=0.5' ou 'damage=r') 
    e aplica aos objetos selecionados.
    """
    # 1. Validações iniciais
    if not input_string or not target_objs: return "Operação cancelada ou sem alvos selecionados."

    if "=" not in input_string: return "Formato inválido. Use 'chave=valor' (ex: light_level=0.5)"

    # 2. Separa a chave e o valor
    key, new_val = input_string.split("=", 1)
    key = key.strip()
    new_val = new_val.strip()

    # 3. Normaliza os alvos para serem sempre uma lista (facilita o loop)
    # Se for uma Entidade única, transformamos numa lista de um elemento.
    if not isinstance(target_objs, list): target_objs = [target_objs]

    sucessos = 0
    removidos = 0

    # 4. Aplica a lógica a todos os objetos alvo
    for obj in target_objs:
        if new_val.lower() == 'r':
            context.remove_attrs(obj, [key], wall_idx) # Remove o atributo
            removidos += 1
        else:
            if context.set_attr(obj, key, new_val, wall_idx): # Define e valida o tipo
                sucessos += 1
            else:
                return f"ERRO: Valor '{new_val}' inválido para o tipo de '{key}'."
    
    # 5. Atualiza a interface gráfica
    ui.rebuild_attr_panel()

    # 6. Retorna a mensagem de feedback
    if removidos > 0:
        return f"Atributo '{key}' removido de {removidos} objeto(s)."
    return f"Atributo '{key}' definido para {new_val} em {sucessos} objeto(s)."

# -----------------------------
# Loop Principal
# -----------------------------
running = True
while running:
    delta_time = clock.tick(30) / 1000.0

    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False

        manager.process_events(event)
            
        # 1. Entrada de Texto (Modo Typing)
        if input_box.active:
            resultado = input_box.handle_event(event)

            if resultado is not None:  # ENTER pressionado
                if input_purpose == "export":
                    msg = context.export_map(resultado)
                    ui.set_message(msg)

                elif input_purpose == "load":
                    msg = context.load_map(resultado)
                    ui.set_message(msg)
                    ui.rebuild_attr_panel()

                elif input_purpose == "attr":
                    alvos = context.selected_entity if context.selected_entity else context.selected_sector
                    msg = apply_attribute_from_text(resultado, alvos)
                    ui.set_message(msg)

                elif input_purpose == "wall_attr":
                    sec, w_idx = input_target
                    msg = apply_attribute_from_text(resultado, [sec], wall_idx=w_idx)
                    ui.set_message(msg)
                    ui.rebuild_attr_panel()
                
                elif input_purpose == "entity":
                    mx, my = pg.mouse.get_pos()
                    grid_map = input_target
                    if resultado:
                        msg = context.add_entity((mx, my), resultado, grid_map)
                        ui.set_message(msg)
                    else:
                        ui.set_message("Criação de entidade cancelada.")
                    ui.rebuild_attr_panel()

                # Restaura o modo visual para a ferramenta que estava ativa antes
                ui.mode = current_tool_name
            continue 

        # 2. Interações com Botões Laterais da UI
        if ui.handle_ui_event(event):
            continue

        # 3. Controles Globais de Zoom (Mousewheel)
        if event.type == pg.MOUSEWHEEL:
            if event.y > 0:
                config.GRID = max(2, config.GRID - 1)
            elif event.y < 0:
                config.GRID = config.GRID + 1
            ui.set_message(f"Zoom ajustado: GRID={config.GRID}")
            ui.rebuild_help_panel()

        # 4. Eventos de Mouse na Área de Desenho (Delegado para o modes.py)
        if event.type == pg.MOUSEBUTTONDOWN:
            mx, my = event.pos
            if mx < config.VIEW_W:
                current_tool.handle_mouse_down(event, context, ui)

        # 5. Teclas Ativas
        elif event.type == pg.KEYDOWN:
            # Primeiro: a ferramenta ativa processa suas próprias teclas (ex: N, Z, DELETE)
            current_tool.handle_key_down(event, context, ui)

            # Segundo: Atalhos globais do sistema
            if event.key == pg.K_ESCAPE:
                running = False
            
            # Alternar entre as ferramentas (TAB)
            elif event.key == pg.K_TAB:
                tool_keys = list(tools.keys())
                next_idx = (tool_keys.index(current_tool_name) + 1) % len(tool_keys)
                current_tool_name = tool_keys[next_idx]
                current_tool = tools[current_tool_name]
                
                ui.set_mode(current_tool_name)
                ui.set_message(f"Modo: {current_tool_name.upper()}")

            # NAVEGAÇÃO DA CÂMERA
            elif event.key == pg.K_LEFT:
                config.CAM_OFFSET_X += config.GRID
            elif event.key == pg.K_RIGHT:
                config.CAM_OFFSET_X -= config.GRID
            elif event.key == pg.K_UP:
                config.CAM_OFFSET_Y += config.GRID
            elif event.key == pg.K_DOWN:
                config.CAM_OFFSET_Y -= config.GRID

            # OUTROS ATALHOS GLOBAIS
            elif event.key == pg.K_e:
                on_export()

            elif event.key == pg.K_b:
                toggle_bsp()

            elif event.key == pg.K_g:
                ui.toggle_grid()
                ui.rebuild_help_panel()

            elif event.key == pg.K_s:
                ui.toggle_snap()
                ui.rebuild_help_panel()

            # EDIÇÃO DE ATRIBUTOS (Abre o TextInputBox)
            elif event.key == pg.K_w and current_tool_name == "select" and context.selected_sector:
                mx, my = pg.mouse.get_pos()
                parede_encontrada = False
                for sec in context.selected_sector:
                    walls_vertices = sec.outer + sec.outer[:1]
                    for i in range(len(sec.outer)):
                        v1, v2 = walls_vertices[i], walls_vertices[i+1]
                        v1_screen = render.map_to_screen(v1)
                        v2_screen = render.map_to_screen(v2)

                        if geo.point_line_distance((mx, my), v1_screen, v2_screen) < 10:
                            ui.set_mode("typing")
                            input_purpose = "wall_attr"
                            input_target = (sec, i)
                            input_box.activate(f"Novo valor para parede {i} (ou 'r' para remover): ")
                            parede_encontrada = True
                            break
                    if parede_encontrada:
                        break
                        
                if not parede_encontrada:
                    ui.set_message("Nenhuma parede próxima.")
            
            elif event.key == pg.K_a and current_tool_name == "select":
                alvos = context.selected_entity if context.selected_entity else context.selected_sector
                if alvos:
                    ui.set_mode("typing")
                    input_purpose = "attr"
                    input_target = alvos
                    input_box.activate("Atributo (ex: damage=10) >")
                else:
                    ui.set_message("Nenhum setor ou entidade selecionada.")
        manager.update(delta_time)
        manager.draw_ui(screen)
            
            

    # --- Lógica de Renderização ---
    screen.fill(config.COL_BG)

    if ui.show_grid:
        render.draw_grid(screen)

    # Reconstrução da BSP para visualização (custoso, mas apenas para debug)
    walls = context.build_walls(context.sectors)
    bsp_root = context.build_bsp_from_walls(walls)

    if ui.show_bsp: 
        # Desenha a BSP (apenas a estrutura, não a renderização do jogo)
        render.draw_bsp(screen, bsp_root)
    else:
        # Desenha setores event paredes no modo editor
        render.draw_sectors_and_walls(screen, context=context,mode=ui.mode)

    render.draw_entities(screen, context=context)
    
    render.draw_current(screen, context=context)
    ui.draw_ui(screen)

    # Atualiza e desenha a caixa de texto por cima de tudo
    input_box.update()
    input_box.draw(screen)
    
    pg.display.flip()

pg.quit()
sys.exit()
