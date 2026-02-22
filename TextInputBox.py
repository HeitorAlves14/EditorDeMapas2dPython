import pygame as pg
import time

class TextInputBox:
    def __init__(self, x, y, w, h, font, bg_color=(40, 40, 45), text_color=(255, 255, 255)):
        self.rect = pg.Rect(x, y, w, h)
        self.color_active = (100, 150, 255)
        self.color_inactive = (70, 70, 80)
        self.bg_color = bg_color
        self.text_color = text_color
        self.font = font
        
        self.text = ""
        self.prompt_text = ""
        self.active = False
        self.done = False
        self.cursor_visible = True
        self.last_cursor_toggle = time.time()

    def activate(self, prompt=""):
        """Ativa a caixa de texto e define a mensagem de prompt."""
        self.active = True
        self.done = False
        self.text = ""
        self.prompt_text = prompt

    def deactivate(self):
        """Desativa a caixa de texto."""
        self.active = False
        self.text = ""

    def handle_event(self, event):
        """Processa os eventos de teclado. Retorna o texto se o Enter for premido."""
        if not self.active:
            return None

        if event.type == pg.KEYDOWN:
            if event.key == pg.K_RETURN or event.key == pg.K_KP_ENTER:
                self.done = True
                result = self.text
                self.deactivate()
                return result
            elif event.key == pg.K_ESCAPE:
                self.deactivate()
                return None
            elif event.key == pg.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                # Adiciona o caractere digitado (ignora teclas de controlo puras)
                if event.unicode:
                    self.text += event.unicode
        return None

    def update(self):
        """Atualiza o piscar do cursor."""
        if self.active:
            if time.time() - self.last_cursor_toggle > 0.5:
                self.cursor_visible = not self.cursor_visible
                self.last_cursor_toggle = time.time()

    def draw(self, screen):
        """Renderiza a caixa de texto no ecrã."""
        if not self.active:
            return

        # Desenhar fundo e borda
        pg.draw.rect(screen, self.bg_color, self.rect)
        color = self.color_active if self.active else self.color_inactive
        pg.draw.rect(screen, color, self.rect, 2)

        # Renderizar texto (Prompt + Input do utilizador)
        display_text = f"{self.prompt_text} {self.text}"
        if self.cursor_visible and self.active:
            display_text += "|"
            
        text_surface = self.font.render(display_text, True, self.text_color)
        
        # Ajustar a largura da caixa se o texto for muito grande
        self.rect.w = max(300, text_surface.get_width() + 20)
        
        screen.blit(text_surface, (self.rect.x + 10, self.rect.y + (self.rect.h - text_surface.get_height()) // 2))