import pygame
from config import WHITE, BLACK, HUB_ACCENT, HUB_BG

class TextInput:
    def __init__(self, x, y, w, h, font, placeholder="Enter text..."):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = WHITE
        self.text = ""
        self.font = font
        self.placeholder = placeholder
        self.active = False
        self.txt_surface = self.font.render(self.text, True, self.color)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            # If the user clicked on the input_box rect.
            if self.rect.collidepoint(event.pos):
                self.active = not self.active
            else:
                self.active = False
            self.color = HUB_ACCENT if self.active else WHITE
            
        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    return self.text
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    self.text += event.unicode
                # Re-render the text.
                self.txt_surface = self.font.render(self.text, True, self.color)
        return None

    def draw(self, screen):
        # Draw background
        pygame.draw.rect(screen, HUB_BG, self.rect)
        # Draw text
        if self.text == "" and not self.active:
            placeholder_surf = self.font.render(self.placeholder, True, (150, 150, 150))
            screen.blit(placeholder_surf, (self.rect.x + 10, self.rect.y + (self.rect.h - placeholder_surf.get_height()) // 2))
        else:
            screen.blit(self.txt_surface, (self.rect.x + 10, self.rect.y + (self.rect.h - self.txt_surface.get_height()) // 2))
        
        # Draw border
        pygame.draw.rect(screen, self.color, self.rect, 2, border_radius=5)

    def reset(self):
        self.text = ""
        self.active = False
        self.txt_surface = self.font.render(self.text, True, self.color)
