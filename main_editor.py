# main_editor.py
import sys
import pygame as pg
import threading
import json
import math

# Importar os módulos
import config
import geometry as geo
import map_manager as mm
import ui
import render
from data_structures import ATTRIBUTE_REGISTRY, Entity, ENTITY_ATTRIBUTE_REGISTRY

# -----------------------------
# Variáveis de Estado
# -----------------------------
# show_grid, use_snap, mode, message movidos para ui.py
# sectors, current_vertices, selected_sector movidos para map_manager.py

# -----------------------------
# Inicialização
# -----------------------------
pg.init()
screen = pg.display.set_mode((config.W, config.H))
pg.display.set_caption("2D Map Editor")

try:
    font = pg.font.SysFont('Consolas', 18)
except:
    font = pg.font.Font(None, 24) # Fallback

ui.init_ui(font)

# -----------------------------
# Funções de Ação (Callbacks)
# -----------------------------

def handle_prompt_input(prompt):
    """Função para simular uma caixa de entrada (bloqueante)."""
    print(prompt, end="")
    try:
        user_input = input()
        return user_input.strip()
    except EOFError:
        return ""

def on_export():
    map_name = handle_prompt_input("Nome da pasta para exportar (ex: 'mapa_fase_1'): ")
    if map_name:
        try:
            # Chama a função atualizada do map_manager
            msg = mm.export_map(map_name) 
            ui.set_message(msg)
        except Exception as e:
            ui.set_message(f"ERRO ao exportar: {e}")
    else:
        ui.set_message("Exportação cancelada.")

def on_load():
    map_name = handle_prompt_input("Nome da pasta para carregar (ex: 'mapa_fase_1'): ")
    if map_name:
        try:
            # Chama a função atualizada do map_manager
            msg = mm.load_map(map_name)
            ui.set_message(msg)
            ui.rebuild_attr_panel() 
        except Exception as e:
            ui.set_message(f"ERRO ao carregar: {e}")
    else:
        ui.set_message("Carregamento cancelado.")

def on_clear():
    msg = mm.clear_map()
    ui.set_message(msg)
    ui.rebuild_attr_panel()

def toggle_bsp():
    ui.toggle_bsp()
    ui.rebuild_ui(on_export, on_load, on_clear, toggle_bsp) # Atualiza o botão

# Reconstruir UI com as novas funções de callback
ui.rebuild_ui(on_export, on_load, on_clear, toggle_bsp)

def handle_entity_creation():
    """Lógica para criar uma entidade após a entrada do tipo."""
    entity_type = handle_prompt_input("Tipo da entidade (skill_level, is_enemy): ")
    mx, my = pg.mouse.get_pos()
    
    if entity_type:
        msg = mm.add_entity((mx, my), entity_type, angle=0.0)
        ui.set_message(msg)
    else:
        ui.set_message("Criação de entidade cancelada.")
    ui.rebuild_attr_panel()

def handle_attribute_input(key, obj ):
    """Lógica para receber entrada de texto do usuário para um atributo."""
    if not obj: return

    prompt = f"Novo valor para {key} (ou 'r' para remover): "
    
    # Simulação de input box (Pygame não tem um fácil)
    # Na prática, você precisaria de uma biblioteca de UI ou uma implementação própria.
    # Aqui, se usa o input() do console como fallback, o que bloqueia o Pygame.
    # Para um editor real, isso deve ser uma janela de diálogo do Pygame.
    
    # Apenas como placeholder:
    print(prompt, end="")
    try:
        new_val = input()
    except EOFError: # Acontece em alguns ambientes de execução
        return
    
    obj_name = "Entidade" if isinstance(obj, Entity) else "Setor"
    obj_id = obj.id
    
    if new_val.lower() == 'r':
        # Usa o 'obj' para remover
        mm.remove_attrs(obj, [key])
        ui.set_message(f"Atributo {key} removido de {obj_name} {obj_id}")
    else:
        # Usa o 'obj' para setar
        if mm.set_attr(obj, key, new_val):
            ui.set_message(f"Atributo {key} definido para {new_val} em {obj_name} {obj_id}")
        else:
            ui.set_message(f"ERRO: Valor inválido para o tipo de {key}.")
    
    ui.rebuild_attr_panel() # Atualiza a UI

# -----------------------------
# Loop Principal
# -----------------------------
running = True
while running:
    for e in pg.event.get():
        if e.type == pg.QUIT:
            running = False

        # Tratar eventos de botão primeiro
        if ui.handle_ui_event(e):
            continue

        # Lógica de Input no painel de visualização
        if e.type == pg.MOUSEBUTTONDOWN and e.button == 1:
            mx, my = e.pos
            if mx < config.VIEW_W: # Clique na área de desenho
                if ui.mode == "draw":
                    # Adicionar vértice
                    mm.add_vertex(mx, my, config.GRID, ui.use_snap)
                    ui.set_message(f"Vértice adicionado: ({mx}, {my})")
                elif ui.mode == "select":#Modo select
                    # Tentar selecionar entidade(Prioridade)
                    msg = mm.pick_entity(mx, my)
                    if mm.selected_entity is None:
                        #Se não selecionou entidade, seleciona setor.
                        msg = mm.pick_sector(mx, my)
                    ui.set_message(msg)
                elif ui.mode == "portal": #Modo portal
                    # Tentar criar portal
                    if mm.try_create_portal_at_point((mx, my)):
                        ui.set_message("Portal criado/alterado.")
                    else:
                        ui.set_message("Nenhuma dica de portal encontrada no local.")
                elif ui.mode == "entity":#Modo entity
                    # Cria entidade na posição do clique
                    handle_entity_creation()
                ui.rebuild_attr_panel()

        elif e.type == pg.MOUSEBUTTONDOWN and e.button == 3:
            if ui.mode == "draw":
                # Fechar polígono
                msg = mm.close_sector()
                ui.set_message(msg)
                ui.rebuild_attr_panel() # Pode mudar a seleção
            elif ui.mode == "select":
                # Limpar seleção
                mm.selected_sector = None
                mm.selected_entity = None
                ui.set_message("Seleção limpa.")
                ui.rebuild_attr_panel()
            elif ui.mode == "entity":
                msg = mm.remove_entity(mm.selected_entity)
                ui.set_message(msg)
                ui.rebuild_attr_panel()

        # Teclas
        elif e.type == pg.KEYDOWN:
            if e.key == pg.K_ESCAPE:
                running = False
            
            elif e.key == pg.K_TAB:
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

            elif e.key == pg.K_e:
                on_export()

            elif e.key == pg.K_b:
                toggle_bsp()

            elif e.key == pg.K_g:
                ui.toggle_grid()
                ui.rebuild_help_panel()

            elif e.key == pg.K_s:
                ui.toggle_snap()
                ui.rebuild_help_panel()

            elif e.key == pg.K_n:
                mm.current_vertices.clear()
                ui.set_message("Limpo vértices atuais.")
                ui.rebuild_attr_panel()

            elif e.key == pg.K_z:
                if mm.current_vertices:
                    mm.current_vertices.pop()
                    ui.set_message("Desfeito último vértice.")
                    ui.rebuild_attr_panel()

            elif e.key == pg.K_DELETE:
                #Prioridade em deletar entidade
                if mm.selected_entity:
                    msg = mm.remove_entity(mm.selected_entity)
                    ui.set_message(msg)
                    ui.rebuild_attr_panel()
                    
                elif mm.selected_sector:
                    mm.sectors.remove(mm.selected_sector)
                    mm.selected_sector = None
                    mm.rebuild_indices()
                    ui.set_message("Setor deletado.")
                    ui.rebuild_attr_panel()

            elif e.key == pg.K_w and ui.mode == "select" and mm.selected_sector:
                # Atributo de parede (Portal ID, Textura, etc.).
                walls_vertices = mm.selected_sector.outer + mm.selected_sector.outer[:1]
                mx, my = pg.mouse.get_pos()

                # Procura a parede mais proxima do cursor.
                for i in range(len(mm.selected_sector.outer)):
                    v1 = walls_vertices[i]
                    v2 = walls_vertices[i+1]

                    # Verifica se o ponto está proximo da linha.
                    d = geo.point_line_distance((mx, my), v1, v2)
                    if d < 10:
                        key = f"wall_{i}"
                        obj = mm.selected_sector
                        handle_attribute_input(key, obj)
                        break
                else:
                    ui.set_message("Nenhuma parede próxima.")
            
            elif e.key == pg.K_a and ui.mode == "select":
                
                # Define o objeto a ser modificado: prioriza Entidade sobre Setor
                obj = mm.selected_entity if mm.selected_entity else mm.selected_sector
                
                if obj:
                    
                    prompt_msg = "Atributo (hp, mass, floor_h, etc.) > "
                    prompt_key = handle_prompt_input(prompt_msg)
                    
                    if prompt_key:
                        handle_attribute_input(prompt_key, obj)
                    else:
                        ui.set_message("Atribuição cancelada.")
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
        # Desenha setores e paredes no modo editor
        render.draw_sectors_and_walls(screen, mode=ui.mode)

    render.draw_entities(screen)
    
    render.draw_current(screen)
    ui.draw_ui(screen)
    
    pg.display.flip()

pg.quit()
sys.exit()
