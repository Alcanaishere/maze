
import pygame
import math
import random
import sys

# ============================================================
# 設定
# ============================================================
SCREEN_W = 960
SCREEN_H = 540
FPS = 60

# マップサイズ（奇数にすること）
MAP_W = 21
MAP_H = 21
CELL = 40          # 1セルのピクセルサイズ（内部ワールド座標）

# レイキャスティング設定
FOV = math.radians(60)   # 視野角 (Scratch の fov=48 相当)
NUM_RAYS = SCREEN_W // 2  # レイ本数（半分解像度で高速化）
MAX_DEPTH = MAP_W * CELL

# 色
COLOR_SKY    = (30,  30,  80)
COLOR_FLOOR  = (50,  50,  50)
COLOR_WALL_N = (180, 180, 180)
COLOR_WALL_E = (140, 140, 140)
COLOR_PLAYER = (255, 200,  0)
COLOR_GOAL   = (0,   255, 100)
COLOR_MAP_BG = (20,  20,  20)
COLOR_MAP_WL = (200, 200, 200)

MINIMAP_SCALE = 6   # ミニマップ 1セル = 6px
MINIMAP_X = 10
MINIMAP_Y = 10

PLAYER_SPEED = 3.0
PLAYER_ROT_SPEED = 0.04   # キーボード回転速度（rad/frame）
MOUSE_SENS = 0.003         # マウス感度

# ============================================================
# 迷路生成（再帰バックトラッカー）
# ============================================================
def generate_maze(w, h):
    """w x h (奇数) の迷路を生成。1=壁, 0=通路"""
    maze = [[1] * w for _ in range(h)]

    def in_bounds(cx, cy):
        return 0 < cx < w - 1 and 0 < cy < h - 1

    def carve(cx, cy):
        maze[cy][cx] = 0
        dirs = [(0, -2), (0, 2), (-2, 0), (2, 0)]
        random.shuffle(dirs)
        for dx, dy in dirs:
            nx, ny = cx + dx, cy + dy
            if in_bounds(nx, ny) and maze[ny][nx] == 1:
                maze[cy + dy // 2][cx + dx // 2] = 0
                carve(nx, ny)

    start_x, start_y = 1, 1
    carve(start_x, start_y)
    # 外枠は必ず壁
    for x in range(w):
        maze[0][x] = maze[h - 1][x] = 1
    for y in range(h):
        maze[y][0] = maze[y][w - 1] = 1
    return maze


def find_floor_cells(maze):
    """通路セルのリストを返す"""
    cells = []
    for y, row in enumerate(maze):
        for x, v in enumerate(row):
            if v == 0:
                cells.append((x, y))
    return cells


# ============================================================
# レイキャスティング
# ============================================================
def cast_ray(maze, px, py, angle):
    """
    DDA法でレイを飛ばし、壁までの距離と向き(水平/垂直)を返す。
    px, py: プレイヤー座標（ピクセル）
    angle:  レイの角度（ラジアン）
    """
    ray_cos = math.cos(angle)
    ray_sin = math.sin(angle)

    # DDA セットアップ
    map_x = int(px / CELL)
    map_y = int(py / CELL)

    # 方向ごとのステップ幅
    if ray_cos == 0:
        delta_x = 1e30
    else:
        delta_x = abs(1 / ray_cos) * CELL

    if ray_sin == 0:
        delta_y = 1e30
    else:
        delta_y = abs(1 / ray_sin) * CELL

    # 最初のステップ
    if ray_cos < 0:
        step_x = -1
        side_dist_x = (px - map_x * CELL) / abs(ray_cos)
    else:
        step_x = 1
        side_dist_x = ((map_x + 1) * CELL - px) / abs(ray_cos)

    if ray_sin < 0:
        step_y = -1
        side_dist_y = (py - map_y * CELL) / abs(ray_sin)
    else:
        step_y = 1
        side_dist_y = ((map_y + 1) * CELL - py) / abs(ray_sin)

    # DDA ループ
    hit = False
    side = 0  # 0=垂直壁(NS方向), 1=水平壁(EW方向)
    for _ in range(MAX_DEPTH):
        if side_dist_x < side_dist_y:
            side_dist_x += delta_x
            map_x += step_x
            side = 0
        else:
            side_dist_y += delta_y
            map_y += step_y
            side = 1

        if map_y < 0 or map_y >= len(maze) or map_x < 0 or map_x >= len(maze[0]):
            break
        if maze[map_y][map_x] == 1:
            hit = True
            break

    if not hit:
        return MAX_DEPTH, side

    if side == 0:
        dist = (map_x - px / CELL + (1 - step_x) / 2) / ray_cos * CELL
    else:
        dist = (map_y - py / CELL + (1 - step_y) / 2) / ray_sin * CELL

    return abs(dist), side


# ============================================================
# 描画
# ============================================================
def draw_3d(surface, maze, px, py, angle, goal_x, goal_y):
    """3Dレイキャスティングビューを描画"""
    w, h = surface.get_size()

    # 空と床
    surface.fill(COLOR_SKY, (0, 0, w, h // 2))
    surface.fill(COLOR_FLOOR, (0, h // 2, w, h // 2))

    ray_angle = angle - FOV / 2
    d_angle = FOV / NUM_RAYS
    slice_w = w // NUM_RAYS

    for i in range(NUM_RAYS):
        dist, side = cast_ray(maze, px, py, ray_angle)

        # 魚眼補正
        corrected = dist * math.cos(ray_angle - angle)
        if corrected <= 0:
            corrected = 0.001

        wall_h = min(int(CELL * h / corrected), h)
        wall_top = h // 2 - wall_h // 2

        # 距離で明暗
        brightness = max(0, min(255, int(255 - corrected * 0.8)))
        if side == 1:
            brightness = int(brightness * 0.7)

        color = (brightness, brightness, brightness)
        pygame.draw.rect(surface, color, (i * slice_w, wall_top, slice_w, wall_h))

        ray_angle += d_angle

    # ゴール方向にアイコン（簡易）
    gx_world = goal_x * CELL + CELL // 2
    gy_world = goal_y * CELL + CELL // 2
    dx = gx_world - px
    dy = gy_world - py
    goal_dist = math.hypot(dx, dy)
    if goal_dist > 0:
        goal_angle = math.atan2(dy, dx)
        rel_angle = goal_angle - angle
        # 角度を -π〜π に正規化
        while rel_angle > math.pi:
            rel_angle -= 2 * math.pi
        while rel_angle < -math.pi:
            rel_angle += 2 * math.pi

        if abs(rel_angle) < FOV / 2:
            screen_x = int((rel_angle / FOV + 0.5) * w)
            icon_h = min(int(CELL * h / max(goal_dist * math.cos(rel_angle), 1)), h // 2)
            icon_y = h // 2 - icon_h // 2
            pygame.draw.rect(surface, COLOR_GOAL,
                             (screen_x - 4, icon_y, 8, icon_h))


def draw_minimap(surface, maze, px, py, angle, goal_x, goal_y):
    """左上にミニマップを描画"""
    s = MINIMAP_SCALE
    mw = len(maze[0]) * s
    mh = len(maze) * s

    # 背景
    pygame.draw.rect(surface, COLOR_MAP_BG, (MINIMAP_X - 1, MINIMAP_Y - 1, mw + 2, mh + 2))

    for y, row in enumerate(maze):
        for x, v in enumerate(row):
            if v == 1:
                pygame.draw.rect(surface, COLOR_MAP_WL,
                                 (MINIMAP_X + x * s, MINIMAP_Y + y * s, s, s))

    # ゴール
    pygame.draw.rect(surface, COLOR_GOAL,
                     (MINIMAP_X + goal_x * s + 1, MINIMAP_Y + goal_y * s + 1, s - 2, s - 2))

    # プレイヤー
    ppx = MINIMAP_X + int(px / CELL * s)
    ppy = MINIMAP_Y + int(py / CELL * s)
    pygame.draw.circle(surface, COLOR_PLAYER, (ppx, ppy), s // 2)

    # 視線
    ex = ppx + int(math.cos(angle) * s * 2)
    ey = ppy + int(math.sin(angle) * s * 2)
    pygame.draw.line(surface, COLOR_PLAYER, (ppx, ppy), (ex, ey), 2)


def draw_compass(surface, angle, font):
    """右下にコンパス（方位）を表示"""
    cx, cy = SCREEN_W - 50, SCREEN_H - 50
    pygame.draw.circle(surface, (60, 60, 60), (cx, cy), 30)
    # N方向
    nx = cx + int(math.cos(-math.pi / 2 - angle) * 22)
    ny = cy + int(math.sin(-math.pi / 2 - angle) * 22)
    pygame.draw.line(surface, (255, 80, 80), (cx, cy), (nx, ny), 3)
    label = font.render("N", True, (255, 80, 80))
    surface.blit(label, (nx - 5, ny - 8))


# ============================================================
# ゲームクラス
# ============================================================
class MazeGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("迷路ゲーム（レイキャスティング）")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 28)
        self.big_font = pygame.font.SysFont(None, 72)

        self.new_game()
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)

    def new_game(self):
        self.maze = generate_maze(MAP_W, MAP_H)
        floors = find_floor_cells(self.maze)

        # プレイヤー開始位置
        start = floors[0]
        self.px = start[0] * CELL + CELL // 2
        self.py = start[1] * CELL + CELL // 2
        self.angle = 0.0  # 右向き（東）

        # ゴール位置（スタートから遠い通路）
        goal = max(floors,
                   key=lambda c: abs(c[0] - start[0]) + abs(c[1] - start[1]))
        self.goal_x, self.goal_y = goal

        self.won = False
        self.win_timer = 0

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key == pygame.K_r:
                    self.new_game()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.won:
                    self.new_game()
            if event.type == pygame.MOUSEMOTION and not self.won:
                dx, _ = event.rel
                self.angle += dx * MOUSE_SENS
        return True

    def move(self, keys):
        if self.won:
            return

        move_x = move_y = 0
        speed = PLAYER_SPEED

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            move_x += math.cos(self.angle) * speed
            move_y += math.sin(self.angle) * speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            move_x -= math.cos(self.angle) * speed
            move_y -= math.sin(self.angle) * speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.angle += PLAYER_ROT_SPEED
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.angle -= PLAYER_ROT_SPEED

        # 衝突判定（壁スライディング）
        margin = 8
        new_px = self.px + move_x
        new_py = self.py + move_y

        if not self._is_wall(new_px, self.py, margin):
            self.px = new_px
        if not self._is_wall(self.px, new_py, margin):
            self.py = new_py

    def _is_wall(self, x, y, margin):
        corners = [
            (x - margin, y - margin),
            (x + margin, y - margin),
            (x - margin, y + margin),
            (x + margin, y + margin),
        ]
        for cx, cy in corners:
            mx, my = int(cx / CELL), int(cy / CELL)
            if 0 <= my < len(self.maze) and 0 <= mx < len(self.maze[0]):
                if self.maze[my][mx] == 1:
                    return True
        return False

    def check_goal(self):
        gx_world = self.goal_x * CELL + CELL // 2
        gy_world = self.goal_y * CELL + CELL // 2
        if math.hypot(self.px - gx_world, self.py - gy_world) < CELL * 0.6:
            self.won = True

    def draw(self):
        # 3Dビュー
        draw_3d(self.screen, self.maze, self.px, self.py, self.angle,
                self.goal_x, self.goal_y)
        # ミニマップ
        draw_minimap(self.screen, self.maze, self.px, self.py, self.angle,
                     self.goal_x, self.goal_y)
        # コンパス
        draw_compass(self.screen, self.angle, self.font)

        # HUD
        hint = self.font.render("WASD / 矢印: 移動  マウス: 回転  R: リセット  ESC: 終了", True, (200, 200, 200))
        self.screen.blit(hint, (10, SCREEN_H - 30))

        goal_hint = self.font.render("緑がゴール（ミニマップ参照）", True, COLOR_GOAL)
        self.screen.blit(goal_hint, (10, SCREEN_H - 55))

        # クリア画面
        if self.won:
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            self.screen.blit(overlay, (0, 0))

            msg1 = self.big_font.render("ゴール！", True, COLOR_GOAL)
            msg2 = self.font.render("クリックして次の迷路へ  /  R キーでリセット", True, (255, 255, 255))
            self.screen.blit(msg1, (SCREEN_W // 2 - msg1.get_width() // 2, SCREEN_H // 2 - 60))
            self.screen.blit(msg2, (SCREEN_W // 2 - msg2.get_width() // 2, SCREEN_H // 2 + 20))

        pygame.display.flip()

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            keys = pygame.key.get_pressed()
            self.move(keys)
            self.check_goal()
            self.draw()
            self.clock.tick(FPS)

        pygame.mouse.set_visible(True)
        pygame.event.set_grab(False)
        pygame.quit()
        sys.exit()


# ============================================================
# エントリーポイント
# ============================================================
if __name__ == "__main__":
    game = MazeGame()
    game.run()