# modes.py
import pygame as pg
import config

class ToolMode:
    """Interface base para as ferramentas."""
    def handle_mouse_down(self, event, context, ui):
        pass
    def handle_key_down(self, event, context, ui):
        pass

class DrawMode(ToolMode):
    def handle_mouse_down(self, event, context, ui):
        if event.button == 1: # Clique Esquerdo
            context.add_vertex(event.pos[0], event.pos[1], config.GRID, ui.use_snap)
            ui.set_message(f"Vértice adicionado.")
        elif event.button == 3: # Clique Direito
            msg = context.close_sector()
            ui.set_message(msg)
            ui.rebuild_attr_panel()

    def handle_key_down(self, event, context, ui):
        if event.key == pg.K_n:
            context.current_vertices.clear()
            ui.set_message("Vértices descartados.")
        elif event.key == pg.K_z and context.current_vertices:
            context.current_vertices.pop()
            ui.set_message("Último vértice desfeito.")

class SelectMode(ToolMode):
    def handle_mouse_down(self, event, context, ui):
        if event.button == 1:
            # 1. Tenta pegar uma entidade primeiro
            msg = context.pick_entity(event.pos[0], event.pos[1], config.GRID)
            
            # 2. Se não pegar entidade, tenta pegar setor
            if context.selected_entity is None:
                keys = pg.key.get_pressed()
                msg = context.pick_sector(event.pos[0], event.pos[1], config.GRID, add=keys[pg.K_LSHIFT])
                
            ui.set_message(msg)
            ui.rebuild_attr_panel()

    def handle_key_down(self, event, context, ui):
        if event.key == pg.K_DELETE:
            if context.selected_entity:
                msg = context.remove_entity(context.selected_entity)
                ui.set_message(msg)
            elif context.selected_sector:
                # Remove os setores da lista principal
                for sec in context.selected_sector:
                    if sec in context.sectors:
                        context.sectors.remove(sec)
                context.selected_sector.clear()
                context.rebuild_indices()
                ui.set_message("Setor(es) removido(s).")
            ui.rebuild_attr_panel()

class PortalMode(ToolMode):
    def handle_mouse_down(self, event, context, ui):
        if event.button == 1:
            success = context.try_create_portal_at_point(event.pos, config.GRID)
            if success:
                ui.set_message("Portal alternado com sucesso.")
            else:
                ui.set_message("Impossível criar portal neste segmento.")
            ui.rebuild_attr_panel()

class EntityMode(ToolMode):
    def handle_mouse_down(self, event, context, ui):
        if event.button == 1: # Clique Esquerdo: Adiciona entidade
            # Por padrão adiciona um tipo genérico. Você pode implementar uma UI 
            # para escolher o tipo depois.
            msg = context.add_entity(event.pos, "generic", config.GRID)
            ui.set_message(msg)
            ui.rebuild_attr_panel()
            
        elif event.button == 3: # Clique Direito: Remove entidade clicada
            context.pick_entity(event.pos[0], event.pos[1], config.GRID)
            if context.selected_entity:
                msg = context.remove_entity(context.selected_entity)
                ui.set_message(msg)
            ui.rebuild_attr_panel()