import pygame
from Constants import *
from levels import *

if False:
    # a hint for cx_freeze
    import pygame._view

class Game:

    def __init__(self, screen, vol):
        self.screen = screen
        self.current_level = 0
        self.tiles = ()
        self.clock = pygame.time.Clock()
        self.game_state = 1
        self.running = True
        self.paused = False
        self.exit = False
        self.moving = False
        self.tiles_visible = False
        self.time_last_shown = 0
        self.to_remove = None
        self.tile_xy = {}
        self.f_xy = []
        self.h_xy = []
        self.d_xy = []

        self.volume = vol
        self.background = pygame.mixer.Channel(2)
        self.background.set_volume(self.volume)
        self.sfx = pygame.mixer.Channel(3)
        self.sfx.set_volume(self.volume)

        self.camera = Camera()
        self.player = None

    def load_level(self, level):
        self.tiles = []
        s_x, s_y = 0, 0
        for a, row in enumerate(level):
            for b, column in enumerate(row):
                x = 64*b
                y = 64*a
                if column != ' ':
                    tile = Tile(column, x, y)
                    if tile.type == START:
                        s_x = x
                        s_y = y
                    if tile.type == FINISH:
                        self.f_xy.append((x, y))
                    elif tile.type == REGEN:
                        self.h_xy.append((x, y))
                    elif tile.type == DISAPPEAR:
                        self.d_xy.append((x, y))
                    self.tiles.append(tile)
                    self.tile_xy[(x, y)] = tile.cost
        return s_x, s_y

    def close_level(self, show_player=True):
        delete_tiles = []
        for tile in self.tiles:
            updated_tiles = []
            if self.is_on_screen(tile):
                delete_tiles.append(tile)
                for tile2 in self.tiles:
                    if tile2 not in delete_tiles:
                        updated_tiles.append(tile2)
            else:
                continue
            self.render(updated_tiles, draw_player=show_player)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.game_state = 0
                    self.running = False
            if not self.running:
                    break
            self.clock.tick(35)
        self.screen.fill((0, 0, 0))
        self.clock.tick(35)

    def open_level(self, show_player=True):
        updated_tile_list = []
        for tile in self.tiles:
            if self.is_on_screen(tile):
                updated_tile_list.append(tile)
            else:
                continue
            self.render(updated_tile_list, draw_player=show_player)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.game_state = 0
                    self.running = False
            if not self.game_state:
                break
            self.clock.tick(35)

    def is_on_screen(self, tile):
        x, y, _, _ = tile.rect
        s_x, s_y, _, _ = self.player.rect
        if x > (s_x + 320) or x < (s_x - 320):
            return False
        if y > (s_y + 256) or y < (s_y - 256):
            return False
        return True

    def main_loop(self):
        self.background.play(BACKGROUND_MUSIC_2, loops=-1, fade_ms=1000)
        while self.running and not self.exit:
            x, y = self.load_level(levels[self.current_level])
            self.player = Player(x, y)
            self.open_level()
            while self.game_state == 1:
                self.handle_events()
                self.tile_events()
                self.render()
                self.game_state = self.check_status()
                self.clock.tick(30)
                if self.paused:
                    self.pause_game()
            if self.game_state == 2 or self.game_state == 3:
                self.level_complete()

    def render(self, tiles=None, text=None, draw_player=True):
        if text is None:
            text = []
        if tiles is None:
            tiles = self.tiles
        self.screen.fill((0, 0, 0))
        self.camera.update(self.player)
        for tile in tiles:
            if draw_player or not self.player.on_square([(tile.rect[0], tile.rect[1])]):
                self.screen.blit(tile.surface, self.camera.apply(tile))
        for t in text:
            words = t[0]
            size = t[1]
            pos = t[2]
            pos_rect = pygame.Rect(pos[0], pos[1], 320, 64)
            self.screen.blit(pygame.font.Font('font.ttf', size).render(
                words, 1, (255, 255, 255)), self.camera.apply(pos_rect))
        if draw_player:
            self.screen.blit(rot_center(self.player.img, self.player.angle), self.camera.apply(self.player))
            self.player.render_ui(self.screen, self.tiles_visible, self.time_last_shown)
        pygame.display.flip()

    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.running = False
            if e.type == pygame.KEYDOWN:
                if not self.moving and not self.tiles_visible:
                    if e.key in (pygame.K_a, pygame.K_LEFT):
                        x, y, _, _ = self.player.rect.move(-64, 0)
                        if (x, y) in self.tile_xy:
                            self.moving = True
                            self.player.start_movement(
                                WEST, self.tile_xy[(x, y)], self.clock, self.render, sfx=self.sfx)
                    elif e.key in (pygame.K_s, pygame.K_DOWN):
                        x, y, _, _ = self.player.rect.move(0, 64)
                        if (x, y) in self.tile_xy:
                            self.moving = True
                            self.player.start_movement(
                                SOUTH, self.tile_xy[(x, y)], self.clock, self.render, sfx=self.sfx)
                    elif e.key in (pygame.K_w, pygame.K_UP):
                        x, y, _, _ = self.player.rect.move(0, -64)
                        if (x, y) in self.tile_xy:
                            self.moving = True
                            self.player.start_movement(
                                NORTH, self.tile_xy[(x, y)], self.clock, self.render, sfx=self.sfx)
                    elif e.key in (pygame.K_d, pygame.K_RIGHT):
                        x, y, _, _ = self.player.rect.move(64, 0)
                        if (x, y) in self.tile_xy:
                            self.moving = True
                            self.player.start_movement(
                                EAST, self.tile_xy[(x, y)], self.clock, self.render, sfx=self.sfx)
                    elif e.key == pygame.K_SPACE:
                        if not self.player.recharging:
                            if self.player.reveal_tiles(self.tiles):
                                self.tiles_visible = True
                                self.time_last_shown = pygame.time.get_ticks()
                                print(self.sfx.get_busy())
                                self.sfx.play(SCAN_SFX)
                    elif e.key == pygame.K_ESCAPE:
                        self.paused = True

    def tile_events(self):
        if (pygame.time.get_ticks() - self.time_last_shown) > HIDE_TIMER and self.tiles_visible:
            for tile in self.tiles:
                tile.hide()
            self.tiles_visible = False
        self.moving = self.player.move()
        self.player.regen_power(self.h_xy)
        x, y, _, _ = self.player.rect
        if self.player.on_square(self.d_xy):
            self.to_remove = [x, y]
        if [x, y] != self.to_remove and self.to_remove is not None and not self.moving:
            updated_tiles = []
            updated_xy = {}
            for tile in self.tiles:
                if [tile.rect[0], tile.rect[1]] != self.to_remove:
                    updated_tiles.append(tile)
                    updated_xy[(tile.rect[0], tile.rect[1])] = tile.cost
            if self.tiles != updated_tiles:
                self.to_remove = None
            self.tiles = updated_tiles
            self.tile_xy = updated_xy

    def check_status(self):
        if not self.running:
            return 0
        elif self.player.on_square(self.f_xy):
            return 2
        elif self.player.no_power():
            return 3
        elif self.exit:
            return 4
        return 1

    def pause_game(self):
        message = pygame.font.Font("font.ttf", 60).render(
            "PAUSED", 1, (255, 0, 0))
        message2 = pygame.font.Font("font.ttf", 23).render(
            "Continue (Esc)", 1, (255, 0, 0))
        message4 = pygame.font.Font("font.ttf", 23).render(
            "Quit (Q)", 1, (255, 0, 0))
        message3 = pygame.font.Font("font.ttf", 23).render(
            "Restart Level (R)", 1, (255, 0, 0))
        message5 = pygame.font.Font('font.ttf', 23).render(
            'Toggle sound (M)', 1, (255, 0, 0))
        self.screen.fill((0, 0, 0))
        self.screen.blit(message, (
            HALF_WIDTH - (message.get_width() // 2), 20 + (message.get_height() // 2)))
        self.screen.blit(message2, (
            HALF_WIDTH - (message2.get_width() // 2), (HALF_HEIGHT - message2.get_height() // 2) - 50))
        self.screen.blit(message3, (
            HALF_WIDTH - (message3.get_width() // 2), (HALF_HEIGHT - message3.get_height() // 2) + 10))
        self.screen.blit(message4, (
            HALF_WIDTH - (message4.get_width() // 2), (HALF_HEIGHT - message4.get_height() // 2) + 70))
        self.screen.blit(message5, (
            HALF_WIDTH - (message5.get_width() // 2), (HALF_HEIGHT - message5.get_height() // 2) + 130))
        pygame.display.flip()
        while self.paused:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.paused = False
                    self.running = False
                elif e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        self.paused = False
                    elif e.key == pygame.K_r:
                        self.paused = False
                        x, y = self.load_level(levels[self.current_level])
                        self.player = Player(x, y)
                        self.open_level()
                    elif e.key == pygame.K_q:
                        self.paused = False
                        self.exit = True
                    elif e.key == pygame.K_m:
                        if self.volume == 0.2:
                            self.volume = 0
                        else:
                            self.volume = 0.2
                        self.sfx.set_volume(self.volume)
                        self.background.set_volume(self.volume)

    def level_complete(self, tutorial_end=False, show_player=True, tutorial=False):
        self.close_level(show_player=show_player)
        if self.game_state == 0:
            return
        if self.game_state == 2:
            self.current_level += 1
            message = pygame.font.Font("font.ttf", 40).render(
                "LEVEL " + str(self.current_level) + " COMPLETE", 1, (255, 255, 255))
        else:
            message = pygame.font.Font("font.ttf", 40).render(
                "GAME OVER", 1, (255, 255, 255))
        if (tutorial or self.current_level < len(levels)) and not tutorial_end:
            self.screen.blit(message, (
                HALF_WIDTH - (message.get_width() // 2), HALF_HEIGHT - (message.get_height() // 2)))
            message2 = pygame.font.Font("font.ttf", 20).render(
                "Press any key to continue", 1, (255, 255, 255))
            self.screen.blit(message2, (
                HALF_WIDTH - (message2.get_width() // 2),
                HALF_HEIGHT - (message2.get_height() // 2) + message.get_height()))
            pygame.display.flip()
            waiting = True
            quitting = False
            while waiting:
                for e in pygame.event.get():
                    if e.type == pygame.QUIT:
                        self.running = False
                        quitting = True
                        self.game_state = 0
                        waiting = False
                    elif e.type == pygame.KEYDOWN:
                        waiting = False
            if not quitting:
                self.game_state = 1
        else:
            self.running = False


class Tutorial(Game):

    def __init__(self, screen):
        self.screen = screen
        self.level = 0
        self.text = None
        self.data = None
        self.running = True
        self.game_state = 1
        self.user_control = True
        self.end = False
        self.draw_player = True
        self.show_tiles = False
        Game.__init__(self, screen, 0)
        self.main_loop()

    def main_loop(self):
        while self.running:
            x, y = self.load_tut_level()
            if self.show_tiles:
                self.player.reveal_tiles(self.tiles)
            self.player = Player(x, y)
            self.open_level(self.draw_player)
            while self.game_state == 1:
                self.render(text=self.text, draw_player=self.draw_player)
                skip = self.handle_events()
                self.tile_events()
                self.game_state = self.check_status()
                if skip and not self.user_control:
                    self.game_state = 2
                self.clock.tick(30)
            if self.game_state in (2, 3):
                if self.game_state == 2:
                    self.level += 3
                    if self.level == len(tut_levels):
                        self.exit = True
                self.level_complete(self.exit, self.draw_player, True)

    def load_tut_level(self):
        current_level = tut_levels[self.level]
        self.text = tut_levels[self.level + 1]
        self.data = tut_levels[self.level + 2]
        self.user_control = self.data[0]
        self.draw_player = self.data[1]
        self.show_tiles = self.data[2]
        x, y = self.load_level(current_level)
        self.player = Player(x, y)
        return x, y

    def handle_events(self):
        skip = False
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.running = False
                self.game_state = 0
            elif e.type == pygame.KEYDOWN:
                skip = True
                if self.user_control:
                    if not self.moving and not self.tiles_visible:
                        if e.key in (pygame.K_a, pygame.K_LEFT):
                            x, y, _, _ = self.player.rect.move(-64, 0)
                            if (x, y) in self.tile_xy:
                                self.moving = True
                                self.player.start_movement(
                                    WEST, self.tile_xy[(x, y)], self.clock, self.render, self.text)
                                self.sfx.play(MOVE_SFX)
                        elif e.key in (pygame.K_s, pygame.K_DOWN):
                            x, y, _, _ = self.player.rect.move(0, 64)
                            if (x, y) in self.tile_xy:
                                self.moving = True
                                self.player.start_movement(
                                    SOUTH, self.tile_xy[(x, y)], self.clock, self.render, self.text)
                                self.sfx.play(MOVE_SFX)
                        elif e.key in (pygame.K_w, pygame.K_UP):
                            x, y, _, _ = self.player.rect.move(0, -64)
                            if (x, y) in self.tile_xy:
                                self.moving = True
                                self.player.start_movement(
                                    NORTH, self.tile_xy[(x, y)], self.clock, self.render, self.text)
                                self.sfx.play(MOVE_SFX)
                        elif e.key in (pygame.K_d, pygame.K_RIGHT):
                            x, y, _, _ = self.player.rect.move(64, 0)
                            if (x, y) in self.tile_xy:
                                self.moving = True
                                self.player.start_movement(
                                    EAST, self.tile_xy[(x, y)], self.clock, self.render, self.text)
                                self.sfx.play(MOVE_SFX)
                        elif e.key == pygame.K_SPACE:
                            if not self.player.recharging:
                                self.player.reveal_tiles(self.tiles)
                                self.tiles_visible = True
                                self.time_last_shown = pygame.time.get_ticks()
                        elif e.key == pygame.K_ESCAPE:
                            self.paused = True
        return skip


class Tile:

    def __init__(self, type, x, y):
        self.type = type
        self.surface = pygame.Surface((64, 64))
        self.rect = pygame.Rect(x, y, 64, 64)
        self.hide_tile = COVERED_TILE_IMG
        if self.type == GREEN:
            self.cost = 10
            self.img = GREEN_TILE_IMG
        elif type == AMBER:
            self.cost = 20
            self.img = AMBER_TILE_IMG
        elif type == RED:
            self.cost = 30
            self.img = RED_TILE_IMG
        elif type == START:
            self.cost = 0
            self.img = START_TILE_IMG
            self.hide_tile = START_TILE_IMG
        elif type == FINISH:
            self.cost = 0
            self.img = FINISH_TILE_IMG
        elif type == REGEN:
            self.cost = 0
            self.img = REGEN_TILE_IMG
        elif type == TRAP:
            self.cost = 1000
            self.img = TRAP_TILE_IMG
        elif type == OBSTACLE:
            self.cost = -1
            self.img = OBSTACLE_TILE_IMG
            self.hide_tile = OBSTACLE_TILE_IMG
        elif type == DISAPPEAR:
            self.cost = 10
            self.img = GHOST_TILE_IMG
        else:
            self.cost = 0
            self.img = COVERED_TILE_IMG
        self.surface.blit(self.hide_tile, (0, 0))

    def show(self):
        self.surface.blit(self.img, (0, 0))

    def hide(self):
        self.surface.blit(self.hide_tile, (0, 0))


class Camera:

    def __init__(self):
        self.state = (0, 0)

    def apply(self, target):
        try:
            return target.rect.move(self.state)
        except AttributeError:
            return target.move(self.state)

    def update(self, target):
        x, y, _, _ = target.rect
        self.state = (HALF_WIDTH - (x + 32), HALF_HEIGHT - (y + 32))


class Player:

    def __init__(self, x, y):
        self.img = PLAYER_IDLE_IMG
        self.rect = pygame.Rect(x, y, 64, 64)
        self.power = 100
        self.time_remaining = HIDE_TIMER
        self.recharging = False
        self.was_visible = False
        self.battery_power = 10
        self.power_loss = 0
        self.d_x = 0
        self.d_y = 0
        self.angle = 270

    def start_movement(self, direction, cost, clock, render, text=[], sfx=None):
        dest_angle = ANGLE_LOOKUP[direction]
        if cost > -1:
            if sfx is not None:
                sfx.play(MOVE_SFX)
            self.img = PLAYER_ACTIVE_IMG
            if self.angle != dest_angle:
                self.rotate(dest_angle, clock, render, text)
            self.d_y, self.d_x = direction
            self.rect = self.rect.move((self.d_x, self.d_y))
            self.power_loss = cost

    def rotate(self, dest_angle, clock, render, text):
        if self.angle - dest_angle == 90 or self.angle - dest_angle == -270:
            adjust = -5
        else:
            adjust = 5
        while True:
            self.angle += adjust
            if self.angle > 360:
                self.angle -= ((self.angle // 360) * 360)
            if self.angle == 0:
                self.angle += 360
            render(text=text)
            clock.tick(80)
            if self.angle == dest_angle:
                break

    def move(self):
        if self.d_x == 0 and self.d_y == 0:
            return False
        self.rect = self.rect.move((self.d_x, self.d_y))
        x, y, _, _ = self.rect
        if x % 64 == 0 and y % 64 == 0:
            self.d_x, self.d_y = 0, 0
            self.power -= self.power_loss
            self.power_loss = 0
            self.img = PLAYER_IDLE_IMG
            return False
        return True

    def reveal_tiles(self, tiles):
        if self.power > 10:
            self.power -= 10
            for tile in tiles:
                if [tile.rect[0], tile.rect[1]] != [self.rect[0], self.rect[1]]:
                    tile.show()
            return True
        return False

    def on_square(self, xy):
        x, y, _, _ = self.rect
        if (x, y) in xy:
            return True
        return False

    def no_power(self):
        if self.power <= 0:
            return True
        return False

    def regen_power(self, h_xy):
        if self.on_square(h_xy):
            self.power = 100

    def update_ui(self, visible, time_last_shown):
        self.battery_power = max(self.power // 10, 0)
        if visible:
            self.time_remaining = HIDE_TIMER - min(HIDE_TIMER, pygame.time.get_ticks() - time_last_shown)
            self.was_visible = True
        elif self.was_visible:
            self.recharging = True
            self.was_visible = False
        if not visible and self.recharging:
            self.time_remaining = min(HIDE_TIMER, (pygame.time.get_ticks() - time_last_shown - HIDE_TIMER) * 2)
            if self.time_remaining == HIDE_TIMER:
                self.recharging = False

    def render_ui(self, screen, visible, time_last_shown):
        self.update_ui(visible, time_last_shown)
        screen.blit(BATTERY[self.battery_power], (-60, -65))
        scan_bar = pygame.Surface(((self.time_remaining // 20), 10))
        if visible:
            scan_bar.fill((0, 204, 204))
        elif self.recharging:
            scan_bar.fill((50, 255, 0))
        else:
            scan_bar.fill((200, 200, 200))
        screen.blit(scan_bar, (370, 25))


def main_menu(screen):
    pygame.display.set_caption('R0m-B4 - Ludum Dare 39')
    pygame.display.set_icon(pygame.image.load('icon.png').convert_alpha())
    backing = pygame.mixer.Channel(1)
    game_logo = pygame.image.load('logo.png').convert_alpha()
    winner_msg = pygame.font.Font('font.ttf', 40).render('GAME COMPLETE', 1, (255, 0, 0))
    tut_comp_msg = pygame.font.Font('font.ttf', 40).render('TUTORIAL COMPLETE', 1, (255, 0, 0))
    tut_msg = pygame.font.Font('font.ttf', 30).render('Tutorial (T)', 1, (132, 50, 50))
    ply_msg = pygame.font.Font('font.ttf', 30).render('Play Game (E)', 1, (132, 50, 50))
    quit_msg = pygame.font.Font('font.ttf', 30).render('Quit (Q)', 1, (132, 50, 50))
    volume = 0.2
    running = True

    while running:
        if not backing.get_busy():
            backing.set_volume(0.1)
            backing.play(BACKGROUND_MUSIC_1, loops=-1, fade_ms=1000)
        screen.fill((132, 132, 132))
        screen.blit(game_logo, (HALF_WIDTH - game_logo.get_width() // 2, 30))
        screen.blit(tut_msg, (HALF_WIDTH - tut_msg.get_width() // 2, HALF_HEIGHT - tut_msg.get_height() // 2 + 30))
        screen.blit(ply_msg, (HALF_WIDTH - ply_msg.get_width() // 2, (HALF_HEIGHT - tut_msg.get_height() // 2) - 30))
        screen.blit(quit_msg, (HALF_WIDTH - quit_msg.get_width() // 2, (HALF_HEIGHT - tut_msg.get_height() // 2) + 90))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key == pygame.K_t:
                    backing.fadeout(1000)
                    tut = Tutorial(screen)
                    if tut.game_state == 0:
                        running = False
                    else:
                        screen.fill((0, 0, 0))
                        screen.blit(tut_comp_msg, (HALF_WIDTH - tut_comp_msg.get_width() // 2,
                                                   HALF_HEIGHT - tut_comp_msg.get_height() // 2))
                        pygame.display.flip()
                        pygame.time.delay(3000)
                elif event.key == pygame.K_e:
                    backing.fadeout(1000)
                    game = Game(screen, volume)
                    game.main_loop()
                    game.background.fadeout(1000)
                    volume = game.volume
                    if game.game_state == 2:
                        screen.fill((0, 0, 0))
                        screen.blit(winner_msg, (HALF_WIDTH - winner_msg.get_width() // 2,
                                                 HALF_HEIGHT - winner_msg.get_height() // 2))
                        pygame.display.flip()
                        pygame.time.delay(3000)
                    elif game.game_state == 0:
                        running = False


def rot_center(image, angle):
    orig_rect = image.get_rect()
    rot_image = pygame.transform.rotate(image, angle)
    rot_rect = orig_rect.copy()
    rot_rect.center = rot_image.get_rect().center
    rot_image = rot_image.subsurface(rot_rect).copy()
    return rot_image

if __name__ == '__main__':
    pygame.init()
    pygame.mixer.init()
    window = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    RED_TILE_IMG = pygame.image.load('red_tile.png').convert()
    AMBER_TILE_IMG = pygame.image.load('amber_tile.png').convert()
    GREEN_TILE_IMG = pygame.image.load('green_tile.png').convert()
    COVERED_TILE_IMG = pygame.image.load('covered_tile.png').convert()
    FINISH_TILE_IMG = pygame.image.load('finish_tile.png').convert()
    START_TILE_IMG = pygame.image.load('start_tile.png').convert()
    REGEN_TILE_IMG = pygame.image.load('regen_tile.png').convert()
    TRAP_TILE_IMG = pygame.image.load('trap_tile.png').convert()
    GHOST_TILE_IMG = pygame.image.load('ghost_tile.png').convert()
    OBSTACLE_TILE_IMG = pygame.image.load('boundary_tile.png').convert()
    PLAYER_IDLE_IMG = pygame.image.load('player_idle.png').convert_alpha()
    PLAYER_ACTIVE_IMG = pygame.image.load('player_active.png').convert_alpha()
    BATTERY = []
    for img in range(11):
        BATTERY.append(pygame.image.load('battery' + str(img) + '.png').convert_alpha())
    BACKGROUND_MUSIC_1 = pygame.mixer.Sound('background.wav')
    BACKGROUND_MUSIC_2 = pygame.mixer.Sound('background2.wav')
    SCAN_SFX = pygame.mixer.Sound('scan.wav')
    MOVE_SFX = pygame.mixer.Sound('move.wav')
    main_menu(window)
