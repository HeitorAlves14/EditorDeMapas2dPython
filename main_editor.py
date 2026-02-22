# main_editor.py
import sys
import pygame as pg

# Importar os módulos
import config
import geometry as geo
import map_manager as mm
import ui
import render
from data_structures import ATTRIBUTE_REGISTRY, Entity, ENTITY_ATTRIBUTE_REGISTRY
from TextInputBox import TextInputBox


# -----------------------------
# Inicialização
# -----------------------------
pg.init()
info = pg.display.Info()
'''config.W = info.current_w
config.H = info.current_h''' # Coloquei isso daqui só para testes
screen = pg.display.set_mode((config.W, config.H))
pg.display.set_caption("2D Map Editor")

try:
    font = pg.font.SysFont('Consolas', 18)
except:
    font = pg.font.Font(None, 24) # Fallback

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
    msg = mm.clear_map()
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
            mm.remove_attrs(obj, [key], wall_idx) # Remove o atributo
            removidos += 1
        else:
            if mm.set_attr(obj, key, new_val, wall_idx): # Define e valida o tipo
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
    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False
            
        # 1. Se a caixa de texto estiver ativa, ELA consome o evento de teclado
        if input_box.active:
            resultado = input_box.handle_event(event)

            if resultado is not None:  # ENTER pressionado
                if input_purpose == "export":
                    msg = mm.export_map(resultado)
                    ui.set_message(msg)

                elif input_purpose == "load":
                    msg = mm.load_map(resultado)
                    ui.set_message(msg)
                    ui.rebuild_attr_panel()

                elif input_purpose == "attr":
                    alvos = mm.selected_entity if mm.selected_entity else mm.selected_sector
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
                        msg = mm.add_entity((mx, my), resultado, grid_map)
                        ui.set_message(msg)
                    else:
                        ui.set_message("Criação de entidade cancelada.")
                    ui.rebuild_attr_panel()

                # Resetar estado
                # Desativa o modo de escrita e volta a selecionar
                ui.mode = "select"
            continue # Impede que as teclas acionem outras funções (como atalhos de ecrã)
        # Tratar eventos de botão primeiro
        if ui.handle_ui_event(event):
            continue

        # Lógica de Input no painel de visualização
        if event.type == pg.MOUSEWHEEL :
            if event.y > 0: # scroll para cima
                config.GRID = max(2, config.GRID - 1) # diminui tamanho da célula
            elif event.y < 0: # scroll para baixo
                config.GRID = config.GRID + 1 # aumenta o tamanho da célula
            ui.set_message(f"Zoom ajustado: GRID={config.GRID}")
            ui.rebuild_help_panel()
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if mx < config.VIEW_W: # Clique na área de desenho
                if ui.mode == "draw":
                    # Adicionar vértice
                    mm.add_vertex(mx, my, config.GRID, ui.use_snap)
                    ui.set_message(f"Vértice adicionado: ({mx}, {my})")
                elif ui.mode == "select":#Modo select
                    # Tentar selecionar entidade(Prioridade)
                    msg = mm.pick_entity(mx, my, config.GRID)
                    if mm.selected_entity is None:
                        #Se não selecionou entidade, seleciona setor.
                        keys = pg.key.get_pressed()
                        add = keys[pg.K_LSHIFT]
                        msg = mm.pick_sector(mx, my, config.GRID, add=add)
                    ui.set_message(msg)
                elif ui.mode == "portal": #Modo portal
                    # Tentar criar portal
                    if mm.try_create_portal_at_point((mx, my), config.GRID):
                        ui.set_message("Portal criado/alterado.")
                    else:
                        ui.set_message("Nenhuma dica de portal encontrada no local.")
                elif ui.mode == "entity": #Modo entity
                    # Cria entidade na posição do clique
                    handle_entity_creation(config.GRID)
                ui.rebuild_attr_panel()

        elif event.type == pg.MOUSEBUTTONDOWN and event.button == 3:
            if ui.mode == "draw":
                # Fechar polígono
                msg = mm.close_sector()
                ui.set_message(msg)
                ui.rebuild_attr_panel() # Pode mudar a seleção
            elif ui.mode == "select":
                # Limpar seleção
                mm.selected_sector = []
                mm.selected_entity = None
                ui.set_message("Seleção limpa.")
                ui.rebuild_attr_panel()
            elif ui.mode == "entity":
                msg = mm.remove_entity(mm.selected_entity)
                ui.set_message(msg)
                ui.rebuild_attr_panel()

        # Teclas
        elif event.type == pg.KEYDOWN:
            if event.key == pg.K_ESCAPE:
                running = False
            
            elif event.key == pg.K_TAB:
                # Ciclagem de modos
                if ui.mode == "draw":
                    ui.set_mode("select")
                elif ui.mode == "select":
                    ui.set_mode("portal")
                    mm.compute_portal_hints() # Recalcula hints ao entrar no modo portal
                elif ui.mode == "portal":
                    ui.set_mode("entity")
                else:
                    ui.set_mode("draw")

            elif event.key == pg.K_LEFT:
                config.CAM_OFFSET_X += config.GRID
            elif event.key == pg.K_RIGHT:
                config.CAM_OFFSET_X -= config.GRID
            elif event.key == pg.K_UP:
                config.CAM_OFFSET_Y += config.GRID
            elif event.key == pg.K_DOWN:
                config.CAM_OFFSET_Y -= config.GRID

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

            elif event.key == pg.K_n:
                mm.current_vertices.clear()
                ui.set_message("Limpo vértices atuais.")
                ui.rebuild_attr_panel()

            elif event.key == pg.K_z:
                if mm.current_vertices:
                    mm.current_vertices.pop()
                    ui.set_message("Desfeito último vértice.")
                    ui.rebuild_attr_panel()

            elif event.key == pg.K_DELETE:
                # Prioridade em deletar entidade
                if mm.selected_entity:
                    msg = mm.remove_entity(mm.selected_entity)
                    ui.set_message(msg)
                    ui.rebuild_attr_panel()
                    
                elif mm.selected_sector:
                    for sec in mm.selected_sector:
                        mm.sectors.remove(sec)
                    mm.selected_sector = []
                    mm.rebuild_indices()
                    ui.set_message("Setor(es) deletado(s).")
                    ui.rebuild_attr_panel()

            elif event.key == pg.K_w and ui.mode == "select" and mm.selected_sector:
                mx, my = pg.mouse.get_pos()
                
                parede_encontrada = False
                for sec in mm.selected_sector:
                    walls_vertices = sec.outer + sec.outer[:1]
                    for i in range(len(sec.outer)):
                        v1 = walls_vertices[i]
                        v2 = walls_vertices[i+1]
                        v1_screen = render.map_to_screen(v1)
                        v2_screen = render.map_to_screen(v2)

                        d = geo.point_line_distance((mx, my), v1_screen, v2_screen)
                        if d < 10:
                            # Ativa a caixa de texto para ESTA parede
                            ui.set_mode("typing")
                            input_purpose = "wall_attr"
                            input_target = (sec, i) # Guardamos o setor e a chave da parede
                            input_box.activate(f"Novo valor para {i} (ou 'r' para remover): ")
                            
                            parede_encontrada = True
                            break
                    if parede_encontrada:
                        break
                        
                if not parede_encontrada:
                    ui.set_message("Nenhuma parede próxima.")
            
            elif event.key == pg.K_a: # Assumindo que 'A' era a tecla para editar atributos
                # Atalho para iniciar a edição de atributos
                if event.key == pg.K_a and ui.mode == "select":
                    alvos = mm.selected_entity if mm.selected_entity else mm.selected_sector
                    
                    if alvos:
                        ui.mode = "typing" # Previne interações indesejadas
                        input_purpose = "attr"
                        input_target = alvos
                        input_box.activate("Atributo (ex: damage=10) >")
                    else:
                        ui.set_message("Nenhum setor ou entidade selecionada.")
            
            

    # --- Lógica de Renderização ---
    screen.fill(config.COL_BG)

    if ui.show_grid:
        render.draw_grid(screen)

    # Reconstrução da BSP para visualização (custoso, mas apenas para debug)
    walls = mm.build_walls(mm.sectors)
    bsp_root = mm.build_bsp_from_walls(walls)

    if ui.show_bsp: 
        # Desenha a BSP (apenas a estrutura, não a renderização do jogo)
        render.draw_bsp(screen, bsp_root)
    else:
        # Desenha setores event paredes no modo editor
        render.draw_sectors_and_walls(screen, mode=ui.mode)

    render.draw_entities(screen)
    
    render.draw_current(screen)
    ui.draw_ui(screen)

    # Atualiza e desenha a caixa de texto por cima de tudo
    input_box.update()
    input_box.draw(screen)
    
    pg.display.flip()

pg.quit()
sys.exit()
