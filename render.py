# render.py
import pygame as pg
import math
import config
import geometry as geo

from data_structures import Entity 

transparent_overlay = pg.Surface((config.VIEW_W, config.H), pg.SRCALPHA)


def draw_grid(screen):
    """Desenha a grade de fundo sincronizada com zoom e offset."""
    start_x = -config.CAM_OFFSET_X % config.GRID
    start_y = -config.CAM_OFFSET_Y % config.GRID

    for x in range(start_x, config.VIEW_W, config.GRID):
        pg.draw.line(screen, config.COL_GRID, (x, 0), (x, config.H))
    for y in range(start_y, config.H, config.GRID):
        pg.draw.line(screen, config.COL_GRID, (0, y), (config.VIEW_W, y))


def draw_current(screen, context):
    """Desenha o polígono em construção."""
    verts = map_list_to_screen(context.current_vertices)
    if len(verts) > 1:
        pg.draw.lines(screen, config.COL_SECTOR, False, verts, 2)
    
    if verts:
        mx, my = pg.mouse.get_pos()
        pg.draw.line(screen, config.COL_SECTOR, verts[-1], (mx, my), 1)

    for v in verts:
        pg.draw.circle(screen, config.COL_VERTEX, v, 4)

def map_to_screen(point):
    """Converte coordenadas do mapa para coordenadas da tela."""
    return (
        point[0] * config.GRID + config.CAM_OFFSET_X,
        point[1] * config.GRID + config.CAM_OFFSET_Y
        )

def map_list_to_screen(points):
    return [map_to_screen(p) for p in points]

def draw_sectors_and_walls(screen, context, mode="select"):
    """Desenha os setores e suas paredes com alta performance."""
    # Limpa a superfície transparente reaproveitando a mesma memória
    transparent_overlay.fill((0, 0, 0, 0))

    for sector in context.sectors:
        screen_outer = map_list_to_screen(sector.outer)
        
        # Preenchimento
        fill_color = list(config.COL_SECTOR_FILL)
        if sector is context.selected_sector: # Note que selected_sector agora pode ser uma lista. Ajuste se necessário: if sector in context.selected_sector:
             fill_color[3] = 120

        # Desenha no overlay global em vez de criar um novo
        if len(screen_outer) >= 3:
            pg.draw.polygon(transparent_overlay, fill_color, screen_outer)
            
            # Contorno direto na tela principal
            color = config.COL_SECTOR_SELECTED if sector is context.selected_sector else config.COL_SECTOR
            pg.draw.polygon(screen, color, screen_outer, 2)

        # Lógica de paredes e portais (mantida igual, só usando o 'context' recebido)
        if len(sector.outer) >= 2:
            for i, (a, b) in enumerate(geo.edges_of(screen_outer)):
                wall_type = context.get_attr(sector, "type", wall_idx=i)
                
                if wall_type == "portal":
                    col = config.COL_PORTAL_CONFIRMED
                    width = 4
                else:
                    # Desenhar as paredes como externas (default)
                    col = config.COL_WALL_OUTER
                    width = 2
                
                # Se estiver no modo 'portal', desenhar hints e portais confirmados
                if mode == "portal":
                    if wall_type == "portal":
                        pg.draw.line(screen, col, a, b, width + 2)
                    
                    # Desenhar dica de portal (só funciona se a lógica do context.portal_hint_segments rodar)
                    for (h1, h2), (h3, h4) in context.portal_hint_segments:
                        if geo.point_line_distance(a, h1, h2) < 1.0 or geo.point_line_distance(b, h1, h2) < 1.0:
                            if geo.almost_colinear(a, b, h1, h2):
                                # Desenha o segmento de intersecção
                                sx, sy = (h1[0]+h2[0])/2, (h1[1]+h2[1])/2
                                pg.draw.circle(screen, config.COL_PORTAL_HINT, (int(sx), int(sy)), 10, 1)

                # Desenhar todas as paredes como padrão no modo 'draw/select'
                if mode != "portal":
                    pg.draw.line(screen, col, a, b, width)

    screen.blit(transparent_overlay, (0, 0))

def draw_entities(screen, context):
    """Desenha todas as entidades no mapa."""
    for e in context.entities:
        pos = map_to_screen(e.pos)
        color = Entity.ICONS.get(e.type, config.COL_TEXT)
        
        # Desenhar o ponto central
        pg.draw.circle(screen, color, pos, 6)
        
        # Desenhar a seta de ângulo (direção)
        angle = e.angle
        end_x = pos[0] + 10 * math.cos(math.radians(angle))
        end_y = pos[1] + 10 * math.sin(math.radians(angle))
        pg.draw.line(screen, color, pos, (end_x, end_y), 2)
        
        # Desenhar um contorno se a entidade estiver selecionada
        if e is context.selected_entity:
            pg.draw.circle(screen, config.COL_SECTOR_SELECTED, pos, 10, 2)

def draw_bsp(screen, bsp_root):
    """Função recursiva para desenhar a árvore BSP (apenas debug)."""
    if bsp_root is None: return

    # Desenhar o divisor (como um segmento que divide o espaço)
    a, b = bsp_root.line
    
    # Estender a linha para debug visual
    line_vec = (b[0] - a[0], b[1] - a[1])
    len_vec = math.hypot(*line_vec)
    if len_vec == 0: len_vec = 1.0
    
    dx, dy = line_vec[0] / len_vec, line_vec[1] / len_vec

    # Pontos de extensão (só para visualização)
    p_start = (int(a[0] - dx * config.VIEW_W), int(a[1] - dy * config.VIEW_W))
    p_end = (int(b[0] + dx * config.VIEW_W), int(b[1] + dy * config.VIEW_W))
    
    # Desenhar linha divisória
    pg.draw.line(screen, config.COL_DIV, p_start, p_end, 1)
    
    # Desenhar segmentos colineares
    for seg in bsp_root.collinear:
        pg.draw.line(screen, (100, 200, 255), seg[0], seg[1], 3)
    
    # Desenhar segmentos que estavam no front e back
    for seg in bsp_root.front_segments:
        pg.draw.line(screen, config.COL_FRONT_ARROW, seg[0], seg[1], 1)

    # Chamada recursiva
    draw_bsp(screen, bsp_root.front)
    draw_bsp(screen, bsp_root.back)

def render_bsp(bsp_root, cam_pos, screen):
    """Renderiza a BSP de trás para frente (Back-to-Front)."""
    if bsp_root is None: return

    line = bsp_root.line
    side = geo.point_side_label(cam_pos, line)
    
    # Desenhar recursivamente de trás para frente (algoritmo básico)
    if side == "front":
        render_bsp(bsp_root.back, cam_pos, screen)
        # desenhar geometria no nó (as paredes colineares)
        for seg in bsp_root.collinear:
            pg.draw.line(screen, config.COL_WALL_OUTER, seg[0], seg[1], 2)
        render_bsp(bsp_root.front, cam_pos, screen)
    elif side == "back":
        render_bsp(bsp_root.front, cam_pos, screen)
        # desenhar geometria no nó
        for seg in bsp_root.collinear:
            pg.draw.line(screen, config.COL_WALL_OUTER, seg[0], seg[1], 2)
        render_bsp(bsp_root.back, cam_pos, screen)
    else: # Colinear
        render_bsp(bsp_root.front, cam_pos, screen)
        render_bsp(bsp_root.back, cam_pos, screen)