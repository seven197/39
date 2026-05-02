"""
Roguelike Survival Game - Mobile Version
使用 Kivy 框架开发，支持触屏控制
完全移植电脑版的所有功能和视觉效果
"""

import math
import random
import time
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.graphics import Color, Ellipse, Line, Rectangle, InstructionGroup
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.properties import NumericProperty, BooleanProperty
from kivy.graphics import PushMatrix, PopMatrix, Rotate

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
Window.size = (SCREEN_WIDTH, SCREEN_HEIGHT)

WHITE = (1, 1, 1, 1)
BLACK = (0, 0, 0, 1)
RED = (1, 0, 0, 1)
GREEN = (0, 1, 0, 1)
BLUE = (0, 0, 1, 1)
YELLOW = (1, 1, 0, 1)
ORANGE = (1, 0.5, 0, 1)
PURPLE = (0.5, 0, 1, 1)
CYAN = (0, 1, 1, 1)
GRAY = (0.5, 0.5, 0.5, 1)


def get_spawn_interval(game_time):
    if game_time < 30:
        return 4.0
    elif game_time < 60:
        return 3.5
    elif game_time < 120:
        return 3.0
    elif game_time < 180:
        return 2.5
    else:
        return 2.0


def get_stat_bounds(game_time):
    if game_time < 60:
        return 30, 60, 0.2, 0.3, 0, 2
    elif game_time < 120:
        return 80, 160, 0.25, 0.4, 2, 6
    elif game_time < 180:
        return 150, 300, 0.3, 0.5, 4, 10
    elif game_time < 300:
        return 250, 500, 0.35, 0.6, 6, 14
    elif game_time < 480:
        return 400, 800, 0.4, 0.7, 10, 20
    else:
        return 600 + (game_time - 480) * 1.5, 1200 + (game_time - 480) * 3, 0.45, 0.8, 12, 25


def get_exp_multiplier(game_time):
    if game_time < 30:
        return 1.0
    elif game_time < 60:
        return 1.5
    elif game_time < 120:
        return 2.0
    elif game_time < 180:
        return 3.0
    elif game_time < 300:
        return 4.0
    else:
        return 5.0


def hex_to_rgba(hex_color):
    hex_color = hex_color.lstrip('#')
    return (
        int(hex_color[0:2], 16) / 255,
        int(hex_color[2:4], 16) / 255,
        int(hex_color[4:6], 16) / 255,
        1
    )


class JoystickWidget(Widget):
    stick_radius = NumericProperty(40)
    base_radius = NumericProperty(80)
    is_active = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size = (200, 200)
        self.center_x = 120
        self.center_y = 120
        self.base_center_x = self.center_x
        self.base_center_y = self.center_y
        self.stick_pos_x = self.center_x
        self.stick_pos_y = self.center_y
        self.touch_id = None
        self.dx = 0
        self.dy = 0

        Clock.schedule_interval(self.draw, 1/60)

    def draw(self, dt):
        self.canvas.clear()
        with self.canvas:
            Color(0.3, 0.3, 0.3, 0.5)
            Ellipse(pos=(self.base_center_x - self.base_radius,
                         self.base_center_y - self.base_radius),
                    size=(self.base_radius * 2, self.base_radius * 2))

            Color(0.6, 0.6, 0.6, 0.8)
            Ellipse(pos=(self.stick_pos_x - self.stick_radius,
                         self.stick_pos_y - self.stick_radius),
                    size=(self.stick_radius * 2, self.stick_radius * 2))

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and not self.touch_id:
            self.touch_id = touch.uid
            self.is_active = True
            self._update_stick(touch.x, touch.y)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.uid == self.touch_id:
            self._update_stick(touch.x, touch.y)
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.uid == self.touch_id:
            self.touch_id = None
            self.is_active = False
            self.stick_pos_x = self.base_center_x
            self.stick_pos_y = self.base_center_y
            self.dx = 0
            self.dy = 0
            return True
        return super().on_touch_up(touch)

    def _update_stick(self, x, y):
        dx = x - self.base_center_x
        dy = y - self.base_center_y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > self.base_radius:
            ratio = self.base_radius / distance
            self.stick_pos_x = self.base_center_x + dx * ratio
            self.stick_pos_y = self.base_center_y + dy * ratio
            self.dx = dx * ratio / self.base_radius
            self.dy = dy * ratio / self.base_radius
        else:
            self.stick_pos_x = x
            self.stick_pos_y = y
            self.dx = dx / self.base_radius
            self.dy = dy / self.base_radius


class Player:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.speed = 0.6
        self.hp = 100
        self.max_hp = 100
        self.exp = 0
        self.exp_to_level = 100
        self.level = 1

        self.weapon = "sword"
        self.weapon_level = 1
        self.attack_cooldown = 0
        self.attack_range = 80
        self.attack_damage = 30
        self.attack_angle = 0
        self.facing_angle = 0
        self.is_attacking = False
        self.attack_timer = 0
        self.sword_hit_monsters = []
        self.zeus_spear_in_hand = True

        self.skills = {}
        self.skill_levels = {}
        self.skill_cooldowns = {}

    def update(self, dx, dy, dt):

        if dx != 0 and dy != 0:
            dx *= 0.707
            dy *= 0.707

        new_x = self.x + dx
        new_y = self.y + dy

        if -SCREEN_WIDTH//2 + 20 < new_x < SCREEN_WIDTH//2 - 20:
            self.x = new_x
        if -SCREEN_HEIGHT//2 + 20 < new_y < SCREEN_HEIGHT//2 - 20:
            self.y = new_y

        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt

        if self.is_attacking:
            self.attack_timer -= dt
            if self.attack_timer <= 0:
                self.is_attacking = False

        for skill in self.skill_cooldowns:
            if self.skill_cooldowns[skill] > 0:
                self.skill_cooldowns[skill] -= dt

    def attack(self, target_x, target_y):
        if self.attack_cooldown <= 0:
            self.is_attacking = True
            self.attack_timer = 0.2
            self.sword_hit_monsters = []

            dx = target_x - self.x
            dy = target_y - self.y
            self.attack_angle = math.degrees(math.atan2(dy, dx))

            if self.weapon == "sword":
                self.attack_cooldown = 0.5
            elif self.weapon == "staff":
                self.attack_cooldown = 0.4
            elif self.weapon == "gun":
                if self.weapon_level >= 10:
                    self.attack_cooldown = 0.5
                elif 6 <= self.weapon_level < 10:
                    self.attack_cooldown = 1.0
                elif self.weapon_level == 4:
                    self.attack_cooldown = 0.25
                else:
                    self.attack_cooldown = 0.8
            elif self.weapon == "zeus_spear":
                self.attack_cooldown = 0.8

            return True
        return False

    def get_attack_damage(self):
        base_damage = self.attack_damage

        if self.weapon == "sword":
            return base_damage + self.weapon_level * 15
        elif self.weapon == "staff":
            return base_damage + self.weapon_level * 8
        elif self.weapon == "gun":
            if self.weapon_level >= 10:
                return 250
            elif self.weapon_level >= 6:
                return (base_damage * 2 + self.weapon_level * 15) * 5
            elif self.weapon_level >= 5:
                return int((base_damage * 2 + self.weapon_level * 15) * 0.7)
            else:
                return base_damage * 2 + self.weapon_level * 15
        elif self.weapon == "zeus_spear":
            if self.weapon_level >= 10:
                return base_damage * 3 + self.weapon_level * 20
            elif self.weapon_level >= 6:
                return base_damage * 2 + self.weapon_level * 15
            elif self.weapon_level >= 4:
                return base_damage * 1.5 + self.weapon_level * 10
            else:
                return base_damage + self.weapon_level * 8
        return base_damage

    def gain_exp(self, amount, multiplier):
        actual_exp = int(amount * multiplier)
        self.exp += actual_exp
        if self.exp >= self.exp_to_level:
            return True
        return False

    def level_up(self):
        self.exp -= self.exp_to_level
        self.level += 1

        if self.level <= 5:
            growth_rate = 1.3
        elif self.level <= 10:
            growth_rate = 1.2
        elif self.level <= 15:
            growth_rate = 1.15
        else:
            growth_rate = 1.1

        self.exp_to_level = int(self.exp_to_level * growth_rate)

    def upgrade_weapon(self):
        self.weapon_level += 1
        if self.weapon == "sword":
            self.attack_damage += 10
            self.attack_range += 5
        elif self.weapon == "staff":
            self.attack_damage += 12
        elif self.weapon == "gun":
            self.attack_damage += 15

    def change_weapon(self, new_weapon, level=1):
        self.weapon = new_weapon
        self.weapon_level = level
        if new_weapon == "sword":
            self.attack_damage = 30 + (level - 1) * 15
            self.attack_range = 80 + (level - 1) * 5
            self.attack_cooldown = 0
        elif new_weapon == "staff":
            self.attack_damage = 35 + (level - 1) * 12
            self.attack_range = 300
            self.attack_cooldown = 0
        elif new_weapon == "gun":
            self.attack_damage = 40 + (level - 1) * 15
            self.attack_range = 500
            self.attack_cooldown = 0
        elif new_weapon == "zeus_spear":
            self.attack_damage = 50 + (level - 1) * 20
            self.attack_range = 500
            self.attack_cooldown = 0

    def unlock_skill(self, skill_name):
        if skill_name not in self.skills:
            self.skills[skill_name] = True
            self.skill_levels[skill_name] = 1
            self.skill_cooldowns[skill_name] = 0
        else:
            self.skill_levels[skill_name] += 1


class Monster:
    def __init__(self, x, y, hp, speed, defense, game_time):
        self.x = x
        self.y = y
        self.hp = hp
        self.max_hp = hp
        self.base_speed = speed
        self.speed = speed
        self.defense = defense
        self.radius = self.calculate_size()
        self.frozen_timer = 0
        self.slow_timer = 0
        self.zeus_marked = False
        self.zeus_marked_timer = 0
        self.color = self.calculate_color()
        self.ring_color = self.calculate_ring_color()
        self.alive = True

    def calculate_size(self):
        min_size = 8
        max_size = 30
        size = min_size + (self.max_hp / 400) * (max_size - min_size)
        return int(min(max_size, max(min_size, size)))

    def calculate_color(self):
        max_speed = 1.0
        min_speed = 0.3

        speed_ratio = (self.base_speed - min_speed) / (max_speed - min_speed)
        speed_ratio = max(0, min(1, speed_ratio))

        r = int(255 - speed_ratio * 100)
        g = int(50 + speed_ratio * 150)
        b = int(50)

        return f"#{r:02x}{g:02x}{b:02x}"

    def calculate_ring_color(self):
        max_defense = 20
        defense_ratio = self.defense / max_defense
        defense_ratio = max(0, min(1, defense_ratio))

        r = int(255 - defense_ratio * 200)
        g = int(255 - defense_ratio * 200)
        b = int(255 - defense_ratio * 55)

        return f"#{r:02x}{g:02x}{b:02x}"

    def update(self, player_x, player_y, dt):
        if self.frozen_timer > 0:
            self.frozen_timer -= dt
            if self.frozen_timer <= 0:
                self.slow_timer = 3.0

        if self.slow_timer > 0:
            self.slow_timer -= dt
            self.speed = self.base_speed * 0.5
            if self.slow_timer <= 0:
                self.speed = self.base_speed

        if self.zeus_marked:
            self.zeus_marked_timer -= dt
            if self.zeus_marked_timer <= 0:
                self.zeus_marked = False

        dx = player_x - self.x
        dy = player_y - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > 0 and self.frozen_timer <= 0:
            self.x += (dx / distance) * self.speed
            self.y += (dy / distance) * self.speed

        self.ring_color = self.calculate_ring_color()

    def take_damage(self, damage):
        actual_damage = max(1, damage - self.defense)
        self.hp -= actual_damage
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def apply_freeze(self, freeze_duration, slow_duration):
        self.frozen_timer = freeze_duration
        self.slow_timer = slow_duration


class RangedMonster:
    def __init__(self, x, y, game_time):
        self.x = x
        self.y = y
        self.game_time = game_time

        if game_time < 180:
            self.hp = 40
        elif game_time < 240:
            self.hp = 60
        elif game_time < 300:
            self.hp = 80
        elif game_time < 360:
            self.hp = 100
        else:
            self.hp = 100 + (game_time - 360) * 0.5

        self.max_hp = self.hp
        self.speed = 0
        self.base_speed = self.speed
        self.defense = 2
        self.radius = 15
        self.alive = True
        self.shoot_timer = 0
        self.shoot_interval = 5.0
        self.frozen_timer = 0
        self.slow_timer = 0
        self.zeus_marked = False

    def update(self, player_x, player_y, dt):
        if self.frozen_timer > 0:
            self.frozen_timer -= dt
            if self.frozen_timer <= 0:
                self.slow_timer = 3.0

        if self.slow_timer > 0:
            self.slow_timer -= dt
            self.speed = self.base_speed * 0.5
            if self.slow_timer <= 0:
                self.speed = self.base_speed

        self.shoot_timer += dt

    def can_shoot(self):
        if self.shoot_timer >= self.shoot_interval:
            self.shoot_timer = 0
            return True
        return False

    def take_damage(self, damage):
        actual_damage = max(1, damage - self.defense)
        self.hp -= actual_damage
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def apply_freeze(self, freeze_duration, slow_duration):
        self.frozen_timer = freeze_duration
        self.slow_timer = slow_duration


class RangedBullet:
    def __init__(self, x, y, target_x, target_y):
        self.x = x
        self.y = y
        self.damage = 5
        self.speed = 1
        self.radius = 6
        self.alive = True

        dx = target_x - x
        dy = target_y - y
        distance = math.sqrt(dx * dx + dy * dy)
        if distance > 0:
            self.vx = (dx / distance) * self.speed
            self.vy = (dy / distance) * self.speed
        else:
            self.vx = self.speed
            self.vy = 0

    def update(self, dt):
        self.x += self.vx
        self.y += self.vy

        if self.x < -SCREEN_WIDTH//2 or self.x > SCREEN_WIDTH//2 or self.y < -SCREEN_HEIGHT//2 or self.y > SCREEN_HEIGHT//2:
            self.alive = False


class Projectile:
    def __init__(self, x, y, target_x, target_y, damage, speed, proj_type, radius=5):
        self.x = x
        self.y = y
        self.damage = damage
        self.speed = speed
        self.proj_type = proj_type
        self.radius = radius
        self.alive = True
        self.pierce_count = 0
        self.max_pierce = 1
        self.hit_monsters = []

        dx = target_x - x
        dy = target_y - y
        distance = math.sqrt(dx * dx + dy * dy)
        if distance > 0:
            self.vx = (dx / distance) * speed
            self.vy = (dy / distance) * speed
        else:
            self.vx = speed
            self.vy = 0

        self.start_x = x
        self.start_y = y
        self.returning = False
        self.hit_edge = False

    def update(self, dt, player_x=0, player_y=0):
        try:
            if self.proj_type == "boomerang":
                if not self.hit_edge:
                    if (self.x <= -SCREEN_WIDTH//2 or self.x >= SCREEN_WIDTH//2 or
                        self.y <= -SCREEN_HEIGHT//2 or self.y >= SCREEN_HEIGHT//2):
                        self.hit_edge = True
                        self.returning = True

                if self.returning:
                    dx = player_x - self.x
                    dy = player_y - self.y
                    distance = math.sqrt(dx * dx + dy * dy)
                    if distance > 0:
                        self.vx = (dx / distance) * self.speed
                        self.vy = (dy / distance) * self.speed

                    if distance < 30:
                        self.alive = False

            self.x += self.vx
            self.y += self.vy

            if self.x < -SCREEN_WIDTH//2 or self.x > SCREEN_WIDTH//2 or self.y < -SCREEN_HEIGHT//2 or self.y > SCREEN_HEIGHT//2:
                if self.proj_type != "boomerang":
                    self.alive = False
        except:
            self.alive = False


class SwordWave:
    def __init__(self, x, y, angle, damage, radius=40, lifetime=0.8, is_ultimate=False):
        self.x = x
        self.y = y
        self.angle = angle
        self.damage = damage
        self.speed = 12
        self.radius = radius
        self.lifetime = lifetime
        self.alive = True
        self.hit_monsters = []
        self.is_ultimate = is_ultimate

    def update(self, dt):
        rad = math.radians(self.angle)
        self.x += self.speed * math.cos(rad)
        self.y += self.speed * math.sin(rad)

        if self.x < -SCREEN_WIDTH//2 or self.x > SCREEN_WIDTH//2 or self.y < -SCREEN_HEIGHT//2 or self.y > SCREEN_HEIGHT//2:
            self.alive = False


class IceCone:
    def __init__(self, x, y, angle, damage):
        self.x = x
        self.y = y
        self.angle = angle
        self.damage = damage
        self.speed = 12
        self.radius = 8
        self.alive = True
        self.lifetime = 2.0
        self.hit_monsters = []

        rad = math.radians(angle)
        self.vx = math.cos(rad) * self.speed
        self.vy = math.sin(rad) * self.speed

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False
            return

        self.x += self.vx
        self.y += self.vy

        if self.x < -SCREEN_WIDTH//2 or self.x > SCREEN_WIDTH//2 or self.y < -SCREEN_HEIGHT//2 or self.y > SCREEN_HEIGHT//2:
            self.alive = False


class ResurrectionOrb:
    def __init__(self, x, y, level, last_killed_hp):
        self.x = x
        self.y = y
        self.level = level
        self.hp = 50 * level + last_killed_hp * 0.1 * level
        self.max_hp = self.hp
        self.speed = 0.5
        self.radius = 15
        self.alive = True
        self.target = None
        self.damage = 30 + level * 10

    def find_target(self, monsters, ranged_monsters, bosses):
        closest = None
        closest_dist = float('inf')

        for monster in monsters:
            dx = monster.x - self.x
            dy = monster.y - self.y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < closest_dist:
                closest_dist = dist
                closest = monster

        for ranged_monster in ranged_monsters:
            dx = ranged_monster.x - self.x
            dy = ranged_monster.y - self.y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < closest_dist:
                closest_dist = dist
                closest = ranged_monster

        for boss in bosses:
            dx = boss.x - self.x
            dy = boss.y - self.y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < closest_dist:
                closest_dist = dist
                closest = boss

        self.target = closest
        return closest_dist

    def update(self, dt, monsters, ranged_monsters, bosses, game):
        self.find_target(monsters, ranged_monsters, bosses)

        if self.target:
            dx = self.target.x - self.x
            dy = self.target.y - self.y
            distance = math.sqrt(dx * dx + dy * dy)
            if distance > 0:
                self.x += (dx / distance) * self.speed
                self.y += (dy / distance) * self.speed

            if distance < self.radius + self.target.radius:
                damage = min(self.hp, self.target.hp)

                self.hp -= damage
                target_killed = self.target.take_damage(damage)

                if target_killed:
                    exp_gained = 20 * get_exp_multiplier(game.game_time)
                    if self.target in monsters or self.target in ranged_monsters:
                        if game.player.gain_exp(exp_gained, 1):
                            game.leveling_up = True
                            game.create_cards()
                    elif self.target in bosses:
                        exp_gained = 100 * get_exp_multiplier(game.game_time)
                        if game.player.gain_exp(exp_gained, 1):
                            game.leveling_up = True
                            game.create_cards()
                    if self.target in monsters:
                        monsters.remove(self.target)
                    elif self.target in ranged_monsters:
                        ranged_monsters.remove(self.target)
                    elif self.target in bosses:
                        bosses.remove(self.target)

                if self.hp > 0:
                    self.find_target(monsters, ranged_monsters, bosses)
                else:
                    self.alive = False

        if self.hp <= 0:
            self.alive = False


class FireAura:
    def __init__(self, x, y, level):
        self.x = x
        self.y = y
        self.level = level
        self.radius = 100 + level * 10
        self.damage = 5 + 5 * level
        self.damage_interval = 0.1
        self.damage_timer = 0
        self.rings = []
        self.ring_color = "#FFA500"
        self.ring_width = 10
        self.ring_lifetime = 0.15

    def update(self, dt, player_x, player_y, monsters, ranged_monsters, bosses, game):
        self.x = player_x
        self.y = player_y

        self.damage_timer += dt
        if self.damage_timer >= self.damage_interval:
            self.damage_timer -= self.damage_interval

            new_ring = {
                "x": self.x,
                "y": self.y,
                "radius": self.radius,
                "age": 0
            }
            self.rings.append(new_ring)

            self.damage_monsters(monsters, ranged_monsters, bosses, game)

        for ring in self.rings[:]:
            ring["age"] += dt
            if ring["age"] >= self.ring_lifetime:
                self.rings.remove(ring)

    def damage_monsters(self, monsters, ranged_monsters, bosses, game):
        for monster in monsters[:]:
            dx = monster.x - self.x
            dy = monster.y - self.y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance <= self.radius + monster.radius:
                if monster.take_damage(self.damage):
                    exp_gained = 20 * get_exp_multiplier(game.game_time)
                    if game.player.gain_exp(exp_gained, 1):
                        game.leveling_up = True
                        game.create_cards()
                    monsters.remove(monster)

        for ranged_monster in ranged_monsters[:]:
            dx = ranged_monster.x - self.x
            dy = ranged_monster.y - self.y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance <= self.radius + ranged_monster.radius:
                if ranged_monster.take_damage(self.damage):
                    exp_gained = 20 * get_exp_multiplier(game.game_time)
                    if game.player.gain_exp(exp_gained, 1):
                        game.leveling_up = True
                        game.create_cards()
                    ranged_monsters.remove(ranged_monster)

        for boss in bosses[:]:
            dx = boss.x - self.x
            dy = boss.y - self.y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance <= self.radius + boss.radius:
                if boss.take_damage(self.damage):
                    exp_gained = 100 * get_exp_multiplier(game.game_time)
                    if game.player.gain_exp(exp_gained, 1):
                        game.leveling_up = True
                        game.create_cards()
                    bosses.remove(boss)


class RotatingSword:
    def __init__(self, x, y, level, mouse_x, mouse_y, launch_angle):
        self.x = x
        self.y = y
        self.level = level
        self.speed = 2.5
        self.rotation_speed = 720
        self.angle = 0
        self.radius = 25 + level * 3
        self.alive = True
        self.flying = True
        self.damage = 25 + 25 * level
        self.damage_interval = 0.5
        self.damage_timer = 0
        self.duration = 2 + 0.25 * level
        self.hit_monsters_this_tick = []

        dx = mouse_x - x
        dy = mouse_y - y
        distance = math.sqrt(dx * dx + dy * dy)
        mouse_angle = 0
        if distance > 0:
            mouse_angle = math.degrees(math.atan2(dy, dx))

        final_angle = mouse_angle + launch_angle
        rad = math.radians(final_angle)
        self.vx = math.cos(rad) * self.speed
        self.vy = math.sin(rad) * self.speed

    def update(self, dt, monsters, ranged_monsters, bosses):
        if not self.alive:
            return

        self.angle += self.rotation_speed * dt
        if self.angle >= 360:
            self.angle -= 360

        if self.flying:
            self.x += self.vx
            self.y += self.vy

            if not (-SCREEN_WIDTH//2 < self.x < SCREEN_WIDTH//2 and -SCREEN_HEIGHT//2 < self.y < SCREEN_HEIGHT//2):
                self.flying = False
            else:
                hit = False
                for monster in monsters:
                    dx = self.x - monster.x
                    dy = self.y - monster.y
                    distance = math.sqrt(dx * dx + dy * dy)
                    if distance <= monster.radius + self.radius:
                        hit = True
                        break

                for ranged_monster in ranged_monsters:
                    dx = self.x - ranged_monster.x
                    dy = self.y - ranged_monster.y
                    distance = math.sqrt(dx * dx + dy * dy)
                    if distance <= ranged_monster.radius + self.radius:
                        hit = True
                        break

                for boss in bosses:
                    dx = self.x - boss.x
                    dy = self.y - boss.y
                    distance = math.sqrt(dx * dx + dy * dy)
                    if distance <= boss.radius + self.radius:
                        hit = True
                        break

                if hit:
                    self.flying = False

        damage_radius = 50

        if self.damage_timer >= self.damage_interval:
            self.damage_timer = 0
            self.hit_monsters_this_tick = []

            for monster in monsters[:]:
                dx = self.x - monster.x
                dy = self.y - monster.y
                distance = math.sqrt(dx * dx + dy * dy)
                if distance <= damage_radius:
                    if monster.take_damage(self.damage):
                        monsters.remove(monster)

            for ranged_monster in ranged_monsters[:]:
                dx = self.x - ranged_monster.x
                dy = self.y - ranged_monster.y
                distance = math.sqrt(dx * dx + dy * dy)
                if distance <= damage_radius:
                    if ranged_monster.take_damage(self.damage):
                        ranged_monsters.remove(ranged_monster)

            for boss in bosses[:]:
                dx = self.x - boss.x
                dy = self.y - boss.y
                distance = math.sqrt(dx * dx + dy * dy)
                if distance <= damage_radius:
                    if boss.take_damage(self.damage):
                        bosses.remove(boss)
        else:
            self.damage_timer += dt

        if not self.flying:
            self.duration -= dt
            if self.duration <= 0:
                self.alive = False


class Boss:
    def __init__(self, x, y, game_time):
        self.x = x
        self.y = y
        self.game_time = game_time
        boss_level = int(game_time // 100) + 1
        self.hp = (500 + boss_level * 200) * 2
        self.max_hp = self.hp
        self.speed = 0.15
        self.base_speed = self.speed
        self.defense = 5 + boss_level * 2
        self.radius = 40
        self.alive = True
        self.shoot_timer = 0
        self.shoot_interval = 10.0
        self.bullet_count = boss_level
        self.frozen_timer = 0
        self.slow_timer = 0
        self.zeus_marked = False
        self.zeus_marked_timer = 0

    def update(self, player_x, player_y, dt):
        if self.frozen_timer > 0:
            self.frozen_timer -= dt
            if self.frozen_timer <= 0:
                self.slow_timer = 3.0

        if self.slow_timer > 0:
            self.slow_timer -= dt
            self.speed = self.base_speed * 0.5
            if self.slow_timer <= 0:
                self.speed = self.base_speed

        if self.zeus_marked:
            self.zeus_marked_timer -= dt
            if self.zeus_marked_timer <= 0:
                self.zeus_marked = False

        dx = player_x - self.x
        dy = player_y - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > 0 and self.frozen_timer <= 0:
            self.x += (dx / distance) * self.speed
            self.y += (dy / distance) * self.speed

        self.shoot_timer += dt

    def can_shoot(self):
        if self.shoot_timer >= self.shoot_interval:
            self.shoot_timer = 0
            return True
        return False

    def take_damage(self, damage):
        actual_damage = max(1, damage - self.defense)
        self.hp -= actual_damage
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def apply_freeze(self, freeze_duration, slow_duration):
        self.frozen_timer = freeze_duration
        self.slow_timer = slow_duration


class BossBullet:
    def __init__(self, x, y, target_x, target_y, damage):
        self.x = x
        self.y = y
        self.damage = 25
        self.speed = 0.5
        self.radius = 15
        self.alive = True

        dx = target_x - x
        dy = target_y - y
        distance = math.sqrt(dx * dx + dy * dy)
        if distance > 0:
            self.vx = (dx / distance) * self.speed
            self.vy = (dy / distance) * self.speed
        else:
            self.vx = self.speed
            self.vy = 0

    def update(self, dt):
        self.x += self.vx
        self.y += self.vy

        if self.x < -SCREEN_WIDTH//2 or self.x > SCREEN_WIDTH//2 or self.y < -SCREEN_HEIGHT//2 or self.y > SCREEN_HEIGHT//2:
            self.alive = False


class ZeusSpear:
    def __init__(self, x, y, target_x, target_y, damage, level):
        self.x = x
        self.y = y
        self.target_x = target_x
        self.target_y = target_y
        self.damage = damage
        self.level = level
        self.speed = 8 + self.level * 0.5
        self.radius = 8
        self.alive = True
        self.returning = False
        self.player_x = x
        self.player_y = y

        dx = target_x - x
        dy = target_y - y
        distance = math.sqrt(dx * dx + dy * dy)
        if distance > 0:
            self.vx = (dx / distance) * self.speed
            self.vy = (dy / distance) * self.speed
        else:
            self.vx = self.speed
            self.vy = 0

    def update(self, dt, player_x, player_y):
        self.player_x = player_x
        self.player_y = player_y

        self.x += self.vx
        self.y += self.vy

        if abs(self.x) > SCREEN_WIDTH//2 or abs(self.y) > SCREEN_HEIGHT//2:
            self.alive = False

        return self.alive

    def get_direction(self):
        dx = self.vx
        dy = self.vy
        angle = math.degrees(math.atan2(dy, dx))
        return angle

    def destroy(self):
        self.alive = False


class Shotgun:
    def __init__(self, x, y, damage, facing_angle):
        self.x = x
        self.y = y
        self.damage = damage
        self.facing_angle = facing_angle
        self.alive = True
        self.bullets = []
        self.spread_angle = 30
        self.bullet_count = 15

        for i in range(self.bullet_count):
            angle_offset = random.uniform(-self.spread_angle, self.spread_angle)
            rad = math.radians(facing_angle + angle_offset)
            target_x = x + 1000 * math.cos(rad)
            target_y = y + 1000 * math.sin(rad)
            bullet = Projectile(x, y, target_x, target_y, damage, 15, "shotgun_pellet", 8)
            bullet.max_pierce = 1
            self.bullets.append(bullet)

    def update(self, dt):
        for bullet in self.bullets[:]:
            bullet.update(dt)
            if not bullet.alive:
                self.bullets.remove(bullet)

        return len(self.bullets) == 0


class Meteor:
    def __init__(self, x, y, damage):
        self.x = x
        self.y = y
        self.damage = damage
        self.radius = 50
        self.alive = True
        self.duration = 1.0
        self.time_elapsed = 0
        self.impact_radius = 200

    def update(self, dt):
        self.time_elapsed += dt
        if self.time_elapsed >= self.duration:
            self.alive = False
            return True
        return False


class Explosion:
    def __init__(self, x, y, damage, radius):
        self.x = x
        self.y = y
        self.damage = damage
        self.radius = radius
        self.max_radius = radius
        self.current_radius = 0
        self.lifetime = 0.3
        self.alive = True
        self.hit_monsters = []

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False


class LightningChain:
    def __init__(self, start_x, start_y, targets):
        self.start_x = start_x
        self.start_y = start_y
        self.targets = targets
        self.lifetime = 0.3
        self.alive = True

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False


class FirePuddle:
    def __init__(self, x, y, damage, duration, radius=50):
        self.x = x
        self.y = y
        self.damage = damage
        self.duration = duration
        self.radius = radius
        self.alive = True
        self.damage_timer = 0
        self.damage_interval = 0.25
        self.hit_monsters_this_tick = []

    def update(self, dt):
        self.duration -= dt
        self.damage_timer += dt

        if self.duration <= 0:
            self.alive = False

    def should_damage(self):
        if self.damage_timer >= self.damage_interval:
            self.damage_timer = 0
            self.hit_monsters_this_tick = []
            return True
        return False


class Molotov:
    def __init__(self, x, y, target_x, target_y, damage, duration, radius=50):
        self.x = x
        self.y = y
        self.target_x = target_x
        self.target_y = target_y
        self.damage = damage
        self.duration = duration
        self.radius = radius
        self.speed = 8
        self.alive = True
        self.landed = False

        dx = target_x - x
        dy = target_y - y
        length = math.sqrt(dx * dx + dy * dy)
        if length > 0:
            self.vx = (dx / length) * self.speed
            self.vy = (dy / length) * self.speed
        else:
            self.vx = 0
            self.vy = self.speed

    def update(self, dt):
        if not self.landed:
            self.x += self.vx
            self.y += self.vy

            dx = self.target_x - self.x
            dy = self.target_y - self.y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance < self.speed:
                self.x = self.target_x
                self.y = self.target_y
                self.landed = True


class Laser:
    def __init__(self, start_x, start_y, target_x, target_y, damage, max_reflections=0):
        self.start_x = start_x
        self.start_y = start_y
        self.damage = damage
        self.lifetime = 0.3
        self.alive = True
        self.hit_monsters = []
        self.max_reflections = max_reflections
        self.segments = []

        dx = target_x - start_x
        dy = target_y - start_y
        length = math.sqrt(dx * dx + dy * dy)
        if length > 0:
            dir_x = dx / length
            dir_y = dy / length
        else:
            dir_x = 1
            dir_y = 0

        self.segments = self.calculate_reflections(start_x, start_y, dir_x, dir_y, max_reflections)

    def calculate_reflections(self, start_x, start_y, dir_x, dir_y, reflections_left):
        segments = []
        current_x = start_x
        current_y = start_y
        current_dir_x = dir_x
        current_dir_y = dir_y

        for _ in range(reflections_left + 1):
            end_x, end_y, hit_wall, normal_x, normal_y = self.find_wall_intersection(
                current_x, current_y, current_dir_x, current_dir_y
            )
            segments.append((current_x, current_y, end_x, end_y))

            if not hit_wall or reflections_left <= 0:
                break

            dot = current_dir_x * normal_x + current_dir_y * normal_y
            current_dir_x = current_dir_x - 2 * dot * normal_x
            current_dir_y = current_dir_y - 2 * dot * normal_y

            current_x = end_x
            current_y = end_y
            reflections_left -= 1

        return segments

    def find_wall_intersection(self, start_x, start_y, dir_x, dir_y):
        half_width = SCREEN_WIDTH // 2
        half_height = SCREEN_HEIGHT // 2

        t_values = []

        if dir_x != 0:
            t_right = (half_width - start_x) / dir_x
            t_left = (-half_width - start_x) / dir_x
            if t_right > 0:
                t_values.append((t_right, 'right', -1, 0))
            if t_left > 0:
                t_values.append((t_left, 'left', 1, 0))

        if dir_y != 0:
            t_top = (half_height - start_y) / dir_y
            t_bottom = (-half_height - start_y) / dir_y
            if t_top > 0:
                t_values.append((t_top, 'top', 0, -1))
            if t_bottom > 0:
                t_values.append((t_bottom, 'bottom', 0, 1))

        if not t_values:
            return start_x + dir_x * 1000, start_y + dir_y * 1000, False, 0, 0

        t_values.sort(key=lambda x: x[0])
        t, wall, normal_x, normal_y = t_values[0]

        end_x = start_x + dir_x * t
        end_y = start_y + dir_y * t

        return end_x, end_y, True, normal_x, normal_y

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False


class Bomb:
    def __init__(self, x, y, damage, radius):
        self.x = x
        self.y = y
        self.damage = damage
        self.explosion_radius = radius
        self.fuse_time = 1.0
        self.exploding = False
        self.explosion_time = 0.3
        self.alive = True
        self.hit_monsters = []

    def update(self, dt):
        if not self.exploding:
            self.fuse_time -= dt
            if self.fuse_time <= 0:
                self.exploding = True
        else:
            self.explosion_time -= dt
            if self.explosion_time <= 0:
                self.alive = False


class Card:
    def __init__(self, x, y, option_index, option_text):
        self.x = x
        self.y = y
        self.width = 150
        self.height = 200
        self.option_index = option_index
        self.option_text = option_text
        self.hovered = False

    def check_hover(self, mouse_x, mouse_y):
        self.hovered = (self.x - self.width//2 <= mouse_x <= self.x + self.width//2 and
                       self.y - self.height//2 <= mouse_y <= self.y + self.height//2)
        return self.hovered

    def check_click(self, mouse_x, mouse_y):
        return self.check_hover(mouse_x, mouse_y)


class Game:
    def __init__(self):
        self.player = Player()
        self.monsters = []
        self.ranged_monsters = []
        self.ranged_bullets = []
        self.bosses = []
        self.boss_bullets = []
        self.projectiles = []
        self.sword_waves = []
        self.lasers = []
        self.bombs = []
        self.explosions = []
        self.molotovs = []
        self.fire_puddles = []
        self.ice_cones = []
        self.meteors = []
        self.zeus_spears = []
        self.shotguns = []
        self.lightning_chains = []
        self.game_time = 0
        self.score = 0
        self.spawn_timer = 0
        self.boss_spawn_timer = 0
        self.ranged_spawn_timer = 0
        self.running = True
        self.game_over = False
        self.leveling_up = False
        self.paused = False
        self.cards = []

        self.skill_timers = {
            "fireball": 0,
            "laser": 0,
            "bomb": 0,
            "boomerang": 0,
            "molotov": 0,
            "ice_cone": 0,
            "resurrection": 0,
            "rotating_sword": 0,
            "fire_aura": 0
        }

        self.last_killed_hp = 0
        self.resurrection_orbs = []
        self.rotating_swords = []
        self.fire_aura = None

        self.weapon_levels = {
            "sword": 1,
            "staff": 1,
            "gun": 1,
            "zeus_spear": 1
        }

        self.mouse_x = 0
        self.mouse_y = 0
        self.mouse_clicked = False
        self.mouse_held = False
        self.last_click_time = 0

    def spawn_monster(self):
        side = random.randint(0, 3)
        if side == 0:
            x = random.randint(-SCREEN_WIDTH//2, SCREEN_WIDTH//2)
            y = SCREEN_HEIGHT//2 + 20
        elif side == 1:
            x = random.randint(-SCREEN_WIDTH//2, SCREEN_WIDTH//2)
            y = -SCREEN_HEIGHT//2 - 20
        elif side == 2:
            x = -SCREEN_WIDTH//2 - 20
            y = random.randint(-SCREEN_HEIGHT//2, SCREEN_HEIGHT//2)
        else:
            x = SCREEN_WIDTH//2 + 20
            y = random.randint(-SCREEN_HEIGHT//2, SCREEN_HEIGHT//2)

        hp_min, hp_max, speed_min, speed_max, defense_min, defense_max = get_stat_bounds(self.game_time)

        hp = random.uniform(hp_min, hp_max)
        speed = random.uniform(speed_min, speed_max)
        defense = random.uniform(defense_min, defense_max)

        monster = Monster(x, y, hp, speed, defense, self.game_time)
        self.monsters.append(monster)

    def spawn_boss(self):
        side = random.randint(0, 3)
        if side == 0:
            x = random.randint(-SCREEN_WIDTH//2, SCREEN_WIDTH//2)
            y = SCREEN_HEIGHT//2 + 20
        elif side == 1:
            x = random.randint(-SCREEN_WIDTH//2, SCREEN_WIDTH//2)
            y = -SCREEN_HEIGHT//2 - 20
        elif side == 2:
            x = -SCREEN_WIDTH//2 - 20
            y = random.randint(-SCREEN_HEIGHT//2, SCREEN_HEIGHT//2)
        else:
            x = SCREEN_WIDTH//2 + 20
            y = random.randint(-SCREEN_HEIGHT//2, SCREEN_HEIGHT//2)

        boss = Boss(x, y, self.game_time)
        self.bosses.append(boss)

    def spawn_ranged_monster(self):
        side = random.randint(0, 3)
        margin = 30
        if side == 0:
            x = random.randint(-SCREEN_WIDTH//2 + margin, SCREEN_WIDTH//2 - margin)
            y = SCREEN_HEIGHT//2 - margin
        elif side == 1:
            x = random.randint(-SCREEN_WIDTH//2 + margin, SCREEN_WIDTH//2 - margin)
            y = -SCREEN_HEIGHT//2 + margin
        elif side == 2:
            x = -SCREEN_WIDTH//2 + margin
            y = random.randint(-SCREEN_HEIGHT//2 + margin, SCREEN_HEIGHT//2 - margin)
        else:
            x = SCREEN_WIDTH//2 - margin
            y = random.randint(-SCREEN_HEIGHT//2 + margin, SCREEN_HEIGHT//2 - margin)

        ranged_monster = RangedMonster(x, y, self.game_time)
        self.ranged_monsters.append(ranged_monster)

    def get_option_text(self, option_index):
        if option_index == 0:
            if self.player.weapon == "sword":
                level = self.player.weapon_level
                base_dmg = 30 + level * 15
                range_val = 80 + level * 5
                text = f"升级剑 Lv.{level}→{level+1}\n伤害: {base_dmg}→{base_dmg+15}\n范围: {range_val}→{range_val+5}"
                if level == 4:
                    text += "\n【进化】金色圣剑!\n攻击发射剑气!"
                elif level == 9:
                    text += "\n【终极进化】屠龙宝刀!\n三枚超级大剑气!\n无限穿透!"
                elif level >= 5 and level < 10:
                    text += "\n【金色圣剑】\n剑气伤害+" + str(level * 15)
                elif level >= 10:
                    text += "\n【屠龙宝刀】\n三枚超级剑气!\n无限穿透!"
                return text
            else:
                inherited_level = self.weapon_levels['sword']
                text = f"切换剑\n继承等级: Lv.{inherited_level}\n近战范围攻击"
                if inherited_level >= 10:
                    text += "\n【屠龙宝刀】"
                elif inherited_level >= 5:
                    text += "\n【金色圣剑】"
                return text
        elif option_index == 1:
            if self.player.weapon == "staff":
                level = self.player.weapon_level
                base_dmg = 35 + level * 12
                next_dmg = 35 + (level + 1) * 12
                if level >= 10:
                    text = f"升级陨石术 Lv.{level}→{level+1}\n伤害: {base_dmg * 5}→{next_dmg * 5}\n【终极进化】\n超大范围陨石!\n伤害5倍!"
                elif level == 9:
                    text = f"升级法杖 Lv.{level}→{level+1}\n伤害: {base_dmg}→{next_dmg}\n【终极进化】陨石术!\n超大范围陨石!\n伤害5倍!"
                elif level >= 5:
                    text = f"升级金色法杖 Lv.{level}→{level+1}\n伤害: {base_dmg}→{next_dmg}\n【金色法杖】\n大火球伤害+" + str(level * 12)
                else:
                    text = f"升级法杖 Lv.{level}→{level+1}\n伤害: {base_dmg}→{next_dmg}"
                    if level == 4:
                        text += "\n【进化】金色法杖!\n发射大火球!\n爆炸半径4倍!"
                return text
            else:
                inherited_level = self.weapon_levels['staff']
                text = f"切换法杖\n继承等级: Lv.{inherited_level}\n远程火球攻击"
                if inherited_level >= 10:
                    text += "\n【陨石术】"
                elif inherited_level >= 5:
                    text += "\n【金色法杖】"
                return text
        elif option_index == 2:
            if self.player.weapon == "gun":
                level = self.player.weapon_level
                if level >= 10:
                    base_dmg = 250
                    next_dmg = 250
                    text = f"升级霰弹枪 Lv.{level}→{level+1}\n伤害: {base_dmg}→{next_dmg}\n【终极进化】\n15发散弹!\n超高伤害!"
                elif level == 9:
                    base_dmg = (40 + level * 15) * 5
                    next_dmg = 250
                    text = f"升级狙击枪 Lv.{level}→{level+1}\n伤害: {base_dmg}→{next_dmg}\n【终极进化】霰弹枪!\n15发散弹!\n超高伤害!"
                elif level < 5:
                    base_dmg = 40 + level * 15
                    next_dmg = 40 + (level + 1) * 15
                    text = f"升级枪 Lv.{level}→{level+1}\n伤害: {base_dmg}→{next_dmg}"
                    if level == 4:
                        text += "\n【进化】冲锋枪!\n长按连发!\n射速大幅提升!"
                elif 5 <= level < 10:
                    base_dmg = int((40 + level * 15) * 0.7)
                    next_dmg = int((40 + (level + 1) * 15) * 0.7)
                    cooldown = max(1.5, 3.0 - (level - 5) * 0.25)
                    next_cooldown = max(1.5, 3.0 - (level - 4) * 0.25)
                    text = f"升级冲锋枪 Lv.{level}→{level+1}\n伤害: {base_dmg}→{next_dmg}\n冷却: {cooldown:.2f}s→{next_cooldown:.2f}s"
                    if level == 5:
                        text += "\n【进化】狙击枪!\n伤害5倍!\n无限穿透!\n单发高伤!"
                return text
            else:
                inherited_level = self.weapon_levels['gun']
                text = f"切换枪\n继承等级: Lv.{inherited_level}\n远程射击"
                if inherited_level >= 10:
                    text += "\n【霰弹枪】"
                elif inherited_level >= 6:
                    text += "\n【狙击枪】"
                elif inherited_level >= 5:
                    text += "\n【冲锋枪】"
                return text
        elif option_index == 3:
            if "fireball" in self.player.skills:
                level = self.player.skill_levels.get("fireball", 1)
                dmg = 40 + level * 20
                radius = 15 + level * 5
                explosion_radius = radius * 2.5
                cooldown = 2.0 - level * 0.1
                text = f"升级火球术 Lv.{level}→{level+1}\n伤害: {dmg}→{dmg+20}\n半径: {radius}→{radius+5}\n爆炸范围: {explosion_radius:.0f}\n间隔: {cooldown:.1f}s→{cooldown-0.1:.1f}s\n自动发射，范围爆炸"
                return text
            else:
                return "解锁火球术\n自动发射火球\n击中目标后产生范围爆炸\n基础伤害: 40\n爆炸范围: 37.5"
        elif option_index == 4:
            if "laser" in self.player.skills:
                level = self.player.skill_levels.get("laser", 1)
                dmg = 25 + level * 10
                reflect = level - 1
                cooldown = 1.5 - level * 0.05
                text = f"升级激光 Lv.{level}→{level+1}\n伤害: {dmg}→{dmg+10}\n折射次数: {reflect}→{reflect+1}\n间隔: {cooldown:.2f}s→{cooldown-0.05:.2f}s\n无限穿透，折射反弹"
                return text
            else:
                return "解锁激光\n发射穿透激光\n可折射反弹\n基础伤害: 25\n折射次数: 0次"
        elif option_index == 5:
            if "bomb" in self.player.skills:
                level = self.player.skill_levels.get("bomb", 1)
                dmg = 120 + level * 60
                radius = 80 + level * 15
                cooldown = 5.0 - level * 0.2
                text = f"升级炸弹 Lv.{level}→{level+1}\n伤害: {dmg}→{dmg+60}\n爆炸范围: {radius}→{radius+15}\n间隔: {cooldown:.1f}s→{cooldown-0.2:.1f}s\n大范围高伤害"
                return text
            else:
                return "解锁炸弹\n放置后爆炸\n大范围高伤害\n基础伤害: 120\n爆炸范围: 80"
        elif option_index == 6:
            if "boomerang" in self.player.skills:
                level = self.player.skill_levels.get("boomerang", 1)
                dmg = 50 + level * 15
                pierce = 3 + (level - 1)
                cooldown = 3.0 - level * 0.1
                text = f"升级回旋镖 Lv.{level}→{level+1}\n伤害: {dmg}→{dmg+15}\n穿透: {pierce}→{pierce+1}次\n间隔: {cooldown:.1f}s→{cooldown-0.1:.1f}s\n自动返回，多重穿透"
                return text
            else:
                return "解锁回旋镖\n发射后自动返回\n可穿透多个目标\n基础伤害: 50\n穿透次数: 3次"
        elif option_index == 7:
            if "molotov" in self.player.skills:
                level = self.player.skill_levels.get("molotov", 1)
                dmg = 15 + level * 5
                cooldown = max(1.5, 3.0 - level * 0.2)
                duration = 3.0 + level * 0.5
                radius = 40 + level * 15
                text = f"升级燃烧瓶 Lv.{level}→{level+1}\n伤害: {dmg}→{dmg+5}\n间隔: {cooldown:.1f}s\n持续: {duration:.1f}s→{duration+0.5:.1f}s\n半径: {radius}→{radius+15}\n地面火焰，持续伤害"
                return text
            else:
                return "解锁燃烧瓶\n落地后产生地面火焰\n对范围内敌人造成持续伤害\n基础伤害: 15\n持续时间: 3秒\n影响范围: 40"
        elif option_index == 8:
            if "ice_cone" in self.player.skills:
                level = self.player.skill_levels.get("ice_cone", 1)
                dmg = 10 + level * 3
                count = level
                cooldown = max(0.25, 1.0 - level * 0.1)
                text = f"升级冰锥 Lv.{level}→{level+1}\n伤害: {dmg}→{dmg+3}\n数量: {count}→{count+1}\n间隔: {cooldown:.2f}s→{max(0.25, cooldown-0.1):.2f}s\n冰冻0.15s+减速3s\n多方向发射"
                return text
            else:
                return "解锁冰锥\n发射冰锥攻击\n可冰冻和减速敌人\n基础伤害: 10\n冰冻时间: 0.15秒\n减速时间: 3秒"
        elif option_index == 9:
            if "resurrection" in self.player.skills:
                level = self.player.skill_levels.get("resurrection", 1)
                hp = 50 * level
                damage = 30 + level * 10
                cooldown = 10.0 - level * 0.5
                if level < 5:
                    count = 1
                    next_count = 2
                    effect_text = "\n5级召唤2个小球"
                elif level < 10:
                    count = 2
                    next_count = 3
                    effect_text = "\n10级召唤3个小球"
                else:
                    count = 3
                    next_count = 3
                    effect_text = "\n已达满级！召唤3个小球"
                text = f"升级秽土转生 Lv.{level}→{level+1}\n生命: {hp}→{hp+50}\n伤害: {damage}→{damage+10}\n间隔: {cooldown:.1f}s→{cooldown-0.5:.1f}s\n召唤数量: {count}→{next_count}{effect_text}\n自动追踪怪物"
                return text
            else:
                return "解锁秽土转生\n生成绿色小球\n自动追踪并攻击怪物\n【1级】召唤1个小球\n基础生命: 50\n基础伤害: 30\n【5级】召唤2个小球\n【10级】召唤3个小球"
        elif option_index == 14:
            if "rotating_sword" in self.player.skills:
                level = self.player.skill_levels.get("rotating_sword", 1)
                damage = 25 + 25 * level
                cooldown = 10.0 - level * 0.5
                duration = 2 + 0.25 * level
                if level < 5:
                    count = 1
                    next_count = 2
                    effect_text = "\n5级发射2把飞剑"
                elif level < 10:
                    count = 2
                    next_count = 3
                    effect_text = "\n10级发射3把飞剑"
                else:
                    count = 3
                    next_count = 3
                    effect_text = "\n已达满级！发射3把飞剑"
                text = f"升级旋转飞剑 Lv.{level}→{level+1}\n伤害: {damage}→{damage+25}\n间隔: {cooldown:.1f}s→{cooldown-0.5:.1f}s\n持续: {duration:.1f}s→{duration+0.25:.1f}s\n飞剑数量: {count}→{next_count}{effect_text}\n范围持续伤害"
                return text
            else:
                return "解锁旋转飞剑\n发射旋转的飞剑\n对范围内敌人造成持续伤害\n【1级】发射1把飞剑\n基础伤害: 25\n持续时间: 2秒\n【5级】发射2把飞剑\n【10级】发射3把飞剑"
        elif option_index == 15:
            if "fire_aura" in self.player.skills:
                level = self.player.skill_levels.get("fire_aura", 1)
                damage = 5 + level * 5
                radius = 100 + level * 10
                text = f"升级火焰领域 Lv.{level}→{level+1}\n伤害: {damage}→{damage+5}\n半径: {radius}→{radius+10}\n间隔: 0.1s\n永久跟随角色\n每0.1秒生成球环，对范围内敌人造成伤害"
                return text
            else:
                return "解锁火焰领域\n以角色为中心\n每0.1秒生成橙黄色球环\n对范围内敌人造成伤害\n【1级】伤害: 10，半径: 110\n【每级】伤害+5，半径+10"
        elif option_index == 10:
            return f"回复满血\n立即恢复所有生命\n当前HP: {int(self.player.hp)}/{self.player.max_hp}"
        elif option_index == 11:
            return f"提升血量上限\n最大HP+20\n当前HP+20\n当前上限: {self.player.max_hp}"
        elif option_index == 12:
            return f"提升速度\n移动速度+0.5\n当前速度: {self.player.speed:.1f}"
        elif option_index == 13:
            if self.player.weapon == "zeus_spear":
                level = self.player.weapon_level
                base_dmg = 50 + level * 20
                next_dmg = 50 + (level + 1) * 20
                if level >= 10:
                    text = f"升级雷霆之矛 Lv.{level}→{level+1}\n伤害: {base_dmg}→{next_dmg}\n【终极进化】\n伤害5倍+等级*30\n闪电链增强!"
                elif level == 9:
                    text = f"升级宙斯之矛 Lv.{level}→{level+1}\n伤害: {base_dmg}→{next_dmg}\n【终极进化】雷霆之矛!\n伤害5倍!\n闪电链增强!"
                elif level == 3:
                    text = f"升级宙斯之矛 Lv.{level}→{level+1}\n伤害: {base_dmg}→{next_dmg}\n【进化】雷霆之矛!\n范围伤害提升!\n闪电链效果!"
                elif level >= 4:
                    text = f"升级雷霆之矛 Lv.{level}→{level+1}\n伤害: {base_dmg}→{next_dmg}\n【雷霆之矛】\n范围伤害+" + str(level * 20)
                else:
                    text = f"升级宙斯之矛 Lv.{level}→{level+1}\n伤害: {base_dmg}→{next_dmg}"
                return text
            else:
                inherited_level = self.weapon_levels.get('zeus_spear', 1)
                text = f"切换到宙斯之矛\n继承等级: Lv.{inherited_level}\n发射闪电形状的长矛\n击中怪物后造成范围伤害"
                if inherited_level >= 10:
                    text += "\n【雷霆之矛】"
                elif inherited_level >= 4:
                    text += "\n【雷霆之矛】"
                return text
        return ""

    def create_cards(self):
        self.cards = []

        weapon_evolve_levels = {
            "sword": 5,
            "staff": 5,
            "gun": 4,
            "zeus_spear": 4
        }

        current_weapon = self.player.weapon
        current_level = self.player.weapon_level
        current_evolved = current_level >= weapon_evolve_levels.get(current_weapon, 999)
        current_maxed = current_level >= 10

        weapon_options = {}
        option_index = 0

        if current_evolved or current_maxed:
            if not current_maxed:
                if current_weapon == "sword":
                    weapon_options[0] = "sword"
                elif current_weapon == "staff":
                    weapon_options[1] = "staff"
                elif current_weapon == "gun":
                    weapon_options[2] = "gun"
                elif current_weapon == "zeus_spear":
                    weapon_options[12] = "zeus_spear"
        else:
            if self.weapon_levels.get("sword", 1) < weapon_evolve_levels["sword"] or self.player.weapon == "sword":
                weapon_options[option_index] = "sword"
                option_index += 1

            if self.weapon_levels.get("staff", 1) < weapon_evolve_levels["staff"] or self.player.weapon == "staff":
                weapon_options[option_index] = "staff"
                option_index += 1

            if self.weapon_levels.get("gun", 1) < weapon_evolve_levels["gun"] or self.player.weapon == "gun":
                weapon_options[option_index] = "gun"
                option_index += 1

            if self.weapon_levels.get("zeus_spear", 1) < weapon_evolve_levels["zeus_spear"] or self.player.weapon == "zeus_spear":
                weapon_options[12] = "zeus_spear"

        skill_options = []
        if "fireball" not in self.player.skills:
            skill_options.append(3)
        if "laser" not in self.player.skills:
            skill_options.append(4)
        if "bomb" not in self.player.skills:
            skill_options.append(5)
        if "boomerang" not in self.player.skills:
            skill_options.append(6)
        if "molotov" not in self.player.skills:
            skill_options.append(7)
        if "ice_cone" not in self.player.skills:
            skill_options.append(8)
        if "resurrection" not in self.player.skills:
            skill_options.append(9)
        if "rotating_sword" not in self.player.skills:
            skill_options.append(14)
        if "fire_aura" not in self.player.skills:
            skill_options.append(15)
        if "fireball" in self.player.skills and self.player.skill_levels.get("fireball", 1) < 10:
            skill_options.append(3)
        if "laser" in self.player.skills and self.player.skill_levels.get("laser", 1) < 10:
            skill_options.append(4)
        if "bomb" in self.player.skills and self.player.skill_levels.get("bomb", 1) < 10:
            skill_options.append(5)
        if "boomerang" in self.player.skills and self.player.skill_levels.get("boomerang", 1) < 10:
            skill_options.append(6)
        if "molotov" in self.player.skills and self.player.skill_levels.get("molotov", 1) < 10:
            skill_options.append(7)
        if "ice_cone" in self.player.skills and self.player.skill_levels.get("ice_cone", 1) < 10:
            skill_options.append(8)
        if "resurrection" in self.player.skills and self.player.skill_levels.get("resurrection", 1) < 10:
            skill_options.append(9)
        if "rotating_sword" in self.player.skills and self.player.skill_levels.get("rotating_sword", 1) < 10:
            skill_options.append(14)
        if "fire_aura" in self.player.skills and self.player.skill_levels.get("fire_aura", 1) < 10:
            skill_options.append(15)

        other_options = [10, 11, 12]

        weights = {}
        for i in weapon_options:
            weapon_name = weapon_options[i]
            if self.player.weapon == weapon_name:
                weights[i] = 10
            else:
                weights[i] = 1
        for i in skill_options:
            weights[i] = 5
        for i in other_options:
            weights[i] = 5

        options = list(weights.keys())
        selected = []
        for _ in range(3):
            if not options:
                break
            available_options = [opt for opt in options if opt not in selected]
            if not available_options:
                break
            total_weight = sum(weights[opt] for opt in available_options)
            if total_weight <= 0:
                break
            r = random.uniform(0, total_weight)
            cumulative = 0
            for opt in available_options:
                cumulative += weights[opt]
                if r <= cumulative:
                    selected.append(opt)
                    break

        card_width = 150
        spacing = 50
        total_width = 3 * card_width + 2 * spacing
        start_x = -total_width // 2 + card_width // 2

        for i, opt in enumerate(selected):
            option_text = self.get_option_text(opt)
            card = Card(start_x + i * (card_width + spacing),
                       0,
                       opt, option_text)
            self.cards.append(card)

    def apply_option(self, option_index):
        evolution_levels = {
            "sword": 5,
            "staff": 5,
            "gun": 4,
            "zeus_spear": 4
        }

        if option_index == 0:
            weapon_name = "sword"
            if self.player.weapon == weapon_name:
                self.player.upgrade_weapon()
                self.weapon_levels[weapon_name] = self.player.weapon_level
            else:
                if self.weapon_levels.get(weapon_name, 1) < evolution_levels[weapon_name] and self.weapon_levels.get(self.player.weapon, 1) < evolution_levels.get(self.player.weapon, 999):
                    current_level = self.player.weapon_level
                    self.weapon_levels[self.player.weapon] = current_level
                    inherited_level = self.weapon_levels[weapon_name]
                    self.player.change_weapon(weapon_name, inherited_level)
        elif option_index == 1:
            weapon_name = "staff"
            if self.player.weapon == weapon_name:
                self.player.upgrade_weapon()
                self.weapon_levels[weapon_name] = self.player.weapon_level
            else:
                if self.weapon_levels.get(weapon_name, 1) < evolution_levels[weapon_name] and self.weapon_levels.get(self.player.weapon, 1) < evolution_levels.get(self.player.weapon, 999):
                    current_level = self.player.weapon_level
                    self.weapon_levels[self.player.weapon] = current_level
                    inherited_level = self.weapon_levels[weapon_name]
                    self.player.change_weapon(weapon_name, inherited_level)
        elif option_index == 2:
            weapon_name = "gun"
            if self.player.weapon == weapon_name:
                self.player.upgrade_weapon()
                self.weapon_levels[weapon_name] = self.player.weapon_level
            else:
                if self.weapon_levels.get(weapon_name, 1) < evolution_levels[weapon_name] and self.weapon_levels.get(self.player.weapon, 1) < evolution_levels.get(self.player.weapon, 999):
                    current_level = self.player.weapon_level
                    self.weapon_levels[self.player.weapon] = current_level
                    inherited_level = self.weapon_levels[weapon_name]
                    self.player.change_weapon(weapon_name, inherited_level)
        elif option_index == 12:
            weapon_name = "zeus_spear"
            if self.player.weapon == weapon_name:
                self.player.upgrade_weapon()
                self.weapon_levels[weapon_name] = self.player.weapon_level
            else:
                if self.weapon_levels.get(weapon_name, 1) < evolution_levels[weapon_name] and self.weapon_levels.get(self.player.weapon, 1) < evolution_levels.get(self.player.weapon, 999):
                    current_level = self.player.weapon_level
                    self.weapon_levels[self.player.weapon] = current_level
                    inherited_level = self.weapon_levels[weapon_name]
                    self.player.change_weapon(weapon_name, inherited_level)
        elif option_index == 3:
            self.player.unlock_skill("fireball")
        elif option_index == 4:
            self.player.unlock_skill("laser")
        elif option_index == 5:
            self.player.unlock_skill("bomb")
        elif option_index == 6:
            self.player.unlock_skill("boomerang")
        elif option_index == 7:
            self.player.unlock_skill("molotov")
        elif option_index == 8:
            self.player.unlock_skill("ice_cone")
        elif option_index == 9:
            if "resurrection" in self.player.skills:
                self.player.skill_levels["resurrection"] = self.player.skill_levels.get("resurrection", 1) + 1
            else:
                self.player.unlock_skill("resurrection")
        elif option_index == 14:
            if "rotating_sword" in self.player.skills:
                self.player.skill_levels["rotating_sword"] = self.player.skill_levels.get("rotating_sword", 1) + 1
            else:
                self.player.unlock_skill("rotating_sword")
        elif option_index == 15:
            if "fire_aura" in self.player.skills:
                self.player.skill_levels["fire_aura"] = self.player.skill_levels.get("fire_aura", 1) + 1
            else:
                self.player.unlock_skill("fire_aura")
        elif option_index == 10:
            self.player.hp = self.player.max_hp
        elif option_index == 11:
            self.player.max_hp += 20
            self.player.hp += 20
        elif option_index == 12:
            self.player.speed += 0.5

    def check_sword_attack(self, monster):
        if not self.player.is_attacking:
            return False

        if monster in self.player.sword_hit_monsters:
            return False

        arm_len = 20
        arm_y = self.player.y + 35 - 12 - 5
        base_angle = self.player.facing_angle

        base_rad = math.radians(base_angle)
        base_cos = math.cos(base_rad)
        base_sin = math.sin(base_rad)

        hand_x = self.player.x + arm_len * base_cos
        hand_y = arm_y + arm_len * base_sin

        dx = monster.x - hand_x
        dy = monster.y - hand_y
        distance = math.sqrt(dx * dx + dy * dy)

        blade_length = 50 + self.player.weapon_level * 5
        effective_range = blade_length + 20

        if distance <= effective_range:
            angle_to_monster = math.degrees(math.atan2(dy, dx))

            swing_progress = self.player.attack_timer / 0.2
            swing_offset = 60 * (1 - swing_progress)
            current_swing_angle = base_angle + swing_offset

            angle_diff = abs(angle_to_monster - current_swing_angle)
            if angle_diff > 180:
                angle_diff = 360 - angle_diff

            if angle_diff <= 60:
                self.player.sword_hit_monsters.append(monster)
                return True
        return False

    def check_projectile_hit(self, projectile, monster):
        dx = projectile.x - monster.x
        dy = projectile.y - monster.y
        distance = math.sqrt(dx * dx + dy * dy)
        return distance <= monster.radius + projectile.radius

    def check_laser_hit(self, laser, monster):
        px = monster.x
        py = monster.y

        for seg in laser.segments:
            x1, y1, x2, y2 = seg

            dx = x2 - x1
            dy = y2 - y1
            length_sq = dx * dx + dy * dy

            if length_sq == 0:
                continue

            t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / length_sq))

            closest_x = x1 + t * dx
            closest_y = y1 + t * dy

            distance = math.sqrt((px - closest_x) ** 2 + (py - closest_y) ** 2)

            if distance <= monster.radius:
                return True

        return False

    def check_bomb_hit(self, bomb, monster):
        if not bomb.exploding:
            return False
        dx = monster.x - bomb.x
        dy = monster.y - bomb.y
        distance = math.sqrt(dx * dx + dy * dy)
        return distance <= bomb.explosion_radius

    def kill_monster(self, monster):
        self.last_killed_hp = monster.max_hp
        self.monsters.remove(monster)

    def kill_ranged_monster(self, ranged_monster):
        self.last_killed_hp = ranged_monster.max_hp
        self.ranged_monsters.remove(ranged_monster)

    def kill_boss(self, boss):
        self.bosses.remove(boss)

    def handle_attack(self):
        if self.player.attack(self.mouse_x, self.mouse_y):
            if self.player.weapon == "sword":
                if self.player.weapon_level >= 10:
                    arm_len = 20
                    arm_y = self.player.y + 35 - 12 - 5
                    base_rad = math.radians(self.player.facing_angle)
                    hand_x = self.player.x + arm_len * math.cos(base_rad)
                    hand_y = arm_y + arm_len * math.sin(base_rad)
                    damage = self.player.get_attack_damage() * 1.5
                    for i in range(3):
                        angle_offset = (i - 1) * 15
                        wave = SwordWave(hand_x, hand_y, self.player.facing_angle + angle_offset,
                                        damage, 60, 1.0, True)
                        self.sword_waves.append(wave)
                elif self.player.weapon_level >= 5:
                    arm_len = 20
                    arm_y = self.player.y + 35 - 12 - 5
                    base_rad = math.radians(self.player.facing_angle)
                    hand_x = self.player.x + arm_len * math.cos(base_rad)
                    hand_y = arm_y + arm_len * math.sin(base_rad)
                    wave = SwordWave(hand_x, hand_y, self.player.facing_angle,
                                    self.player.get_attack_damage())
                    self.sword_waves.append(wave)
            elif self.player.weapon == "staff":
                if self.player.weapon_level >= 10:
                    damage = self.player.get_attack_damage() * 5
                    meteor = Meteor(self.mouse_x, self.mouse_y, damage)
                    self.meteors.append(meteor)
                elif self.player.weapon_level >= 5:
                    proj = Projectile(self.player.x, self.player.y,
                                    self.mouse_x, self.mouse_y,
                                    self.player.get_attack_damage() * 2, 8, "big_fireball", 20)
                    proj.max_pierce = 999
                    self.projectiles.append(proj)
                else:
                    proj = Projectile(self.player.x, self.player.y,
                                    self.mouse_x, self.mouse_y,
                                    self.player.get_attack_damage(), 10, "staff_bullet", 6)
                    self.projectiles.append(proj)
            elif self.player.weapon == "gun":
                if self.player.weapon_level >= 10:
                    damage = 250
                    shotgun = Shotgun(self.player.x, self.player.y, damage, self.player.facing_angle)
                    self.shotguns.append(shotgun)
                    for bullet in shotgun.bullets:
                        self.projectiles.append(bullet)
                elif 4 <= self.player.weapon_level < 6:
                    proj = Projectile(self.player.x, self.player.y,
                                    self.mouse_x, self.mouse_y,
                                    self.player.get_attack_damage(), 12, "gun_bullet", 4)
                    self.projectiles.append(proj)
                elif 6 <= self.player.weapon_level < 10:
                    proj = Projectile(self.player.x, self.player.y,
                                    self.mouse_x, self.mouse_y,
                                    self.player.get_attack_damage(), 20, "sniper_bullet", 8)
                    proj.max_pierce = 999
                    self.projectiles.append(proj)
                else:
                    proj = Projectile(self.player.x, self.player.y,
                                    self.mouse_x, self.mouse_y,
                                    self.player.get_attack_damage(), 15, "gun_bullet", 4)
                    self.projectiles.append(proj)
            elif self.player.weapon == "zeus_spear":
                if not self.zeus_spears:
                    damage = self.player.get_attack_damage()
                    level = self.player.weapon_level

                    if level >= 10:
                        spear_count = 7
                    elif level >= 6:
                        spear_count = 5
                    elif level >= 4:
                        spear_count = 3
                    else:
                        spear_count = 1

                    angles = []
                    base_angle = self.player.facing_angle

                    for i in range(spear_count):
                        if i == 0:
                            angles.append(base_angle)
                        elif i == 1 or i == 2:
                            spread = random.uniform(-10, 10)
                            angles.append(base_angle + spread)
                        else:
                            spread = random.uniform(-25, 25)
                            angles.append(base_angle + spread)

                    for angle in angles:
                        rad = math.radians(angle)
                        target_x = self.player.x + 1000 * math.cos(rad)
                        target_y = self.player.y + 1000 * math.sin(rad)
                        spear = ZeusSpear(self.player.x, self.player.y, target_x, target_y, damage, level)
                        self.zeus_spears.append(spear)
                    self.player.zeus_spear_in_hand = False

    def use_skills(self):
        for skill in self.player.skills:
            if self.skill_timers[skill] <= 0:
                level = self.player.skill_levels.get(skill, 1)

                if skill == "fireball":
                    fireball_radius = 15 + level * 5
                    proj = Projectile(self.player.x, self.player.y,
                                    self.mouse_x, self.mouse_y,
                                    40 + level * 20, 8, "fireball", fireball_radius)
                    proj.max_pierce = 999
                    self.projectiles.append(proj)
                    self.skill_timers[skill] = 2.0 - level * 0.1

                elif skill == "laser":
                    reflections = level - 1
                    laser = Laser(self.player.x, self.player.y,
                                self.mouse_x, self.mouse_y,
                                25 + level * 10, reflections)
                    self.lasers.append(laser)
                    self.skill_timers[skill] = 1.5 - level * 0.05

                elif skill == "bomb":
                    bomb = Bomb(self.mouse_x, self.mouse_y,
                              120 + level * 60, 80 + level * 15)
                    self.bombs.append(bomb)
                    self.skill_timers[skill] = 5.0 - level * 0.2

                elif skill == "boomerang":
                    proj = Projectile(self.player.x, self.player.y,
                                    self.mouse_x, self.mouse_y,
                                    50 + level * 15, 5, "boomerang", 40)
                    proj.max_pierce = 4
                    self.projectiles.append(proj)
                    self.skill_timers[skill] = 3.0 - level * 0.1

                elif skill == "molotov":
                    damage = 15 + level * 5
                    duration = 3.0 + level * 0.5
                    radius = 40 + level * 15
                    molotov = Molotov(self.player.x, self.player.y,
                                    self.mouse_x, self.mouse_y,
                                    damage, duration, radius)
                    self.molotovs.append(molotov)
                    self.skill_timers[skill] = max(1.5, 3.0 - level * 0.2)

                elif skill == "ice_cone":
                    cone_count = level
                    base_angle = self.player.facing_angle
                    damage = 10 + level * 3

                    angles = []
                    for i in range(cone_count):
                        if i == 0:
                            angles.append(base_angle)
                        elif i == 1 or i == 2:
                            spread = random.uniform(-10, 10)
                            angles.append(base_angle + spread)
                        else:
                            spread = random.uniform(-25, 25)
                            angles.append(base_angle + spread)

                    for angle in angles:
                        ice = IceCone(self.player.x, self.player.y, angle, damage)
                        self.ice_cones.append(ice)

                    self.skill_timers[skill] = max(0.25, 1.0 - level * 0.1)

                elif skill == "resurrection":
                    if level >= 10:
                        count = 3
                    elif level >= 5:
                        count = 2
                    else:
                        count = 1

                    for _ in range(count):
                        orb = ResurrectionOrb(self.player.x, self.player.y, level, self.last_killed_hp)
                        self.resurrection_orbs.append(orb)

                    self.skill_timers[skill] = 10.0 - level * 0.5

                elif skill == "rotating_sword":
                    mouse_x, mouse_y = self.mouse_x, self.mouse_y

                    if level >= 10:
                        count = 3
                    elif level >= 5:
                        count = 2
                    else:
                        count = 1

                    for i in range(count):
                        launch_angle = (360 / count) * i
                        sword = RotatingSword(self.player.x, self.player.y, level, mouse_x, mouse_y, launch_angle)
                        self.rotating_swords.append(sword)

                    self.skill_timers[skill] = 10.0 - level * 0.5

                elif skill == "fire_aura":
                    if not self.fire_aura:
                        self.fire_aura = FireAura(self.player.x, self.player.y, level)
                    else:
                        self.fire_aura.level = level
                        self.fire_aura.radius = 100 + level * 10
                        self.fire_aura.damage = 5 + 5 * level

                    self.skill_timers[skill] = 0.1

    def update(self, move_dx, move_dy, dt):
        if self.game_over or self.leveling_up or self.paused:
            return

        self.game_time += dt
        self.score += dt

        dx = self.mouse_x - self.player.x
        dy = self.mouse_y - self.player.y
        self.player.facing_angle = math.degrees(math.atan2(dy, dx))

        self.player.update(move_dx, move_dy, dt)

        self.spawn_timer += dt
        spawn_interval = get_spawn_interval(self.game_time)
        if self.spawn_timer >= spawn_interval:
            self.spawn_monster()
            self.spawn_timer = 0

        self.boss_spawn_timer += dt
        if self.boss_spawn_timer >= 100:
            self.spawn_boss()
            self.boss_spawn_timer = 0

        self.ranged_spawn_timer += dt
        if self.game_time >= 150 and self.ranged_spawn_timer >= 8:
            self.spawn_ranged_monster()
            self.ranged_spawn_timer = 0

        self.use_skills()

        for monster in self.monsters[:]:
            monster.update(self.player.x, self.player.y, dt)

            dx = monster.x - self.player.x
            dy = monster.y - self.player.y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance < monster.radius + 20:
                damage = monster.hp / 10
                self.player.hp -= damage
                self.monsters.remove(monster)
                if self.player.hp <= 0:
                    self.game_over = True
                    break

        for boss in self.bosses[:]:
            boss.update(self.player.x, self.player.y, dt)

            if boss.can_shoot():
                for i in range(boss.bullet_count):
                    bullet = BossBullet(boss.x, boss.y, self.player.x, self.player.y, 50 + boss.game_time // 10)
                    self.boss_bullets.append(bullet)

            dx = boss.x - self.player.x
            dy = boss.y - self.player.y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance < boss.radius + 20:
                self.player.hp -= 20 * dt
                if self.player.hp <= 0:
                    self.game_over = True

        for ranged_monster in self.ranged_monsters[:]:
            ranged_monster.update(self.player.x, self.player.y, dt)

            if ranged_monster.can_shoot():
                bullet = RangedBullet(ranged_monster.x, ranged_monster.y, self.player.x, self.player.y)
                self.ranged_bullets.append(bullet)

            dx = ranged_monster.x - self.player.x
            dy = ranged_monster.y - self.player.y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance < ranged_monster.radius + 20:
                self.player.hp -= 5 * dt
                if self.player.hp <= 0:
                    self.game_over = True

        for bullet in self.ranged_bullets[:]:
            bullet.update(dt)

            if not bullet.alive:
                self.ranged_bullets.remove(bullet)
                continue

            dx = bullet.x - self.player.x
            dy = bullet.y - self.player.y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance < bullet.radius + 20:
                self.player.hp -= bullet.damage
                bullet.alive = False
                if self.player.hp <= 0:
                    self.game_over = True

        for bullet in self.boss_bullets[:]:
            bullet.update(dt)

            if not bullet.alive:
                self.boss_bullets.remove(bullet)
                continue

            dx = bullet.x - self.player.x
            dy = bullet.y - self.player.y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance < bullet.radius + 20:
                self.player.hp -= bullet.damage
                bullet.alive = False
                if self.player.hp <= 0:
                    self.game_over = True

        if self.player.weapon == "sword":
            for monster in self.monsters[:]:
                if self.check_sword_attack(monster):
                    damage = self.player.get_attack_damage()
                    if monster.take_damage(damage):
                        exp_gained = 20 * get_exp_multiplier(self.game_time)
                        if self.player.gain_exp(exp_gained, 1):
                            self.leveling_up = True
                            self.create_cards()
                        self.last_killed_hp = monster.max_hp
                        self.monsters.remove(monster)

            for ranged_monster in self.ranged_monsters[:]:
                if self.check_sword_attack(ranged_monster):
                    damage = self.player.get_attack_damage()
                    if ranged_monster.take_damage(damage):
                        exp_gained = 20 * get_exp_multiplier(self.game_time)
                        if self.player.gain_exp(exp_gained, 1):
                            self.leveling_up = True
                            self.create_cards()
                        self.last_killed_hp = ranged_monster.max_hp
                        self.ranged_monsters.remove(ranged_monster)

            for boss in self.bosses[:]:
                if self.check_sword_attack(boss):
                    damage = self.player.get_attack_damage()
                    if boss.take_damage(damage):
                        exp_gained = 100 * get_exp_multiplier(self.game_time)
                        if self.player.gain_exp(exp_gained, 1):
                            self.leveling_up = True
                            self.create_cards()
                        self.last_killed_hp = boss.max_hp
                        self.bosses.remove(boss)

        for proj in self.projectiles[:]:
            proj.update(dt, self.player.x, self.player.y)

            if not proj.alive:
                self.projectiles.remove(proj)
                continue

            targets_to_check = list(self.monsters) + list(self.ranged_monsters) + list(self.bosses)

            for target in targets_to_check:
                if target in proj.hit_monsters:
                    continue
                if self.check_projectile_hit(proj, target):
                    proj.hit_monsters.append(target)
                    damage = proj.damage
                    if target.take_damage(damage):
                        if target in self.monsters:
                            exp_gained = 20 * get_exp_multiplier(self.game_time)
                            if self.player.gain_exp(exp_gained, 1):
                                self.leveling_up = True
                                self.create_cards()
                            self.last_killed_hp = target.max_hp
                            self.monsters.remove(target)
                        elif target in self.ranged_monsters:
                            exp_gained = 20 * get_exp_multiplier(self.game_time)
                            if self.player.gain_exp(exp_gained, 1):
                                self.leveling_up = True
                                self.create_cards()
                            self.last_killed_hp = target.max_hp
                            self.ranged_monsters.remove(target)
                        elif target in self.bosses:
                            exp_gained = 100 * get_exp_multiplier(self.game_time)
                            if self.player.gain_exp(exp_gained, 1):
                                self.leveling_up = True
                                self.create_cards()
                            self.last_killed_hp = target.max_hp
                            self.bosses.remove(target)

                    if proj.proj_type == "staff_bullet":
                        explosion_damage = proj.damage // 2
                        explosion = Explosion(proj.x, proj.y, explosion_damage, 40)
                        self.explosions.append(explosion)

                    if proj.proj_type == "big_fireball":
                        explosion_radius = proj.radius * 4
                        explosion_damage = proj.damage
                        explosion = Explosion(proj.x, proj.y, explosion_damage, explosion_radius)
                        self.explosions.append(explosion)
                        proj.alive = False
                        break

                    if proj.proj_type == "fireball":
                        explosion_radius = proj.radius * 2.5
                        explosion_damage = proj.damage
                        explosion = Explosion(proj.x, proj.y, explosion_damage, explosion_radius)
                        self.explosions.append(explosion)
                        proj.alive = False
                        break

                    proj.pierce_count += 1
                    if proj.pierce_count >= proj.max_pierce:
                        proj.alive = False
                    break

        for wave in self.sword_waves[:]:
            wave.update(dt)

            if not wave.alive:
                self.sword_waves.remove(wave)
                continue

            for monster in self.monsters[:]:
                if monster in wave.hit_monsters:
                    continue
                dx = monster.x - wave.x
                dy = monster.y - wave.y
                distance = math.sqrt(dx * dx + dy * dy)
                if distance <= wave.radius + monster.radius:
                    wave.hit_monsters.append(monster)
                    if monster.take_damage(wave.damage):
                        exp_gained = 20 * get_exp_multiplier(self.game_time)
                        if self.player.gain_exp(exp_gained, 1):
                            self.leveling_up = True
                            self.create_cards()
                        self.last_killed_hp = monster.max_hp
                        self.monsters.remove(monster)

            for boss in self.bosses[:]:
                if boss in wave.hit_monsters:
                    continue
                dx = boss.x - wave.x
                dy = boss.y - wave.y
                distance = math.sqrt(dx * dx + dy * dy)
                if distance <= wave.radius + boss.radius:
                    wave.hit_monsters.append(boss)
                    if boss.take_damage(wave.damage):
                        exp_gained = 100 * get_exp_multiplier(self.game_time)
                        if self.player.gain_exp(exp_gained, 1):
                            self.leveling_up = True
                            self.create_cards()
                        self.last_killed_hp = boss.max_hp
                        self.bosses.remove(boss)

            for ranged_monster in self.ranged_monsters[:]:
                if ranged_monster in wave.hit_monsters:
                    continue
                dx = ranged_monster.x - wave.x
                dy = ranged_monster.y - wave.y
                distance = math.sqrt(dx * dx + dy * dy)
                if distance <= wave.radius + ranged_monster.radius:
                    wave.hit_monsters.append(ranged_monster)
                    if ranged_monster.take_damage(wave.damage):
                        exp_gained = 20 * get_exp_multiplier(self.game_time)
                        if self.player.gain_exp(exp_gained, 1):
                            self.leveling_up = True
                            self.create_cards()
                        self.last_killed_hp = ranged_monster.max_hp
                        self.ranged_monsters.remove(ranged_monster)

        for laser in self.lasers[:]:
            laser.update(dt)

            if not laser.alive:
                self.lasers.remove(laser)
                continue

            for monster in self.monsters[:]:
                if monster in laser.hit_monsters:
                    continue
                if self.check_laser_hit(laser, monster):
                    laser.hit_monsters.append(monster)
                    damage = laser.damage
                    if monster.take_damage(damage):
                        exp_gained = 20 * get_exp_multiplier(self.game_time)
                        if self.player.gain_exp(exp_gained, 1):
                            self.leveling_up = True
                            self.create_cards()
                        self.last_killed_hp = monster.max_hp
                        self.monsters.remove(monster)

            for boss in self.bosses[:]:
                if boss in laser.hit_monsters:
                    continue
                if self.check_laser_hit(laser, boss):
                    laser.hit_monsters.append(boss)
                    damage = laser.damage
                    if boss.take_damage(damage):
                        exp_gained = 100 * get_exp_multiplier(self.game_time)
                        if self.player.gain_exp(exp_gained, 1):
                            self.leveling_up = True
                            self.create_cards()
                        self.last_killed_hp = boss.max_hp
                        self.bosses.remove(boss)

            for ranged_monster in self.ranged_monsters[:]:
                if ranged_monster in laser.hit_monsters:
                    continue
                if self.check_laser_hit(laser, ranged_monster):
                    laser.hit_monsters.append(ranged_monster)
                    damage = laser.damage
                    if ranged_monster.take_damage(damage):
                        exp_gained = 20 * get_exp_multiplier(self.game_time)
                        if self.player.gain_exp(exp_gained, 1):
                            self.leveling_up = True
                            self.create_cards()
                        self.last_killed_hp = ranged_monster.max_hp
                        self.ranged_monsters.remove(ranged_monster)

        for bomb in self.bombs[:]:
            bomb.update(dt)

            if not bomb.alive:
                self.bombs.remove(bomb)
                continue

            if bomb.exploding:
                for monster in self.monsters[:]:
                    if monster not in bomb.hit_monsters:
                        if self.check_bomb_hit(bomb, monster):
                            bomb.hit_monsters.append(monster)
                            damage = bomb.damage
                            if monster.take_damage(damage):
                                exp_gained = 20 * get_exp_multiplier(self.game_time)
                                if self.player.gain_exp(exp_gained, 1):
                                    self.leveling_up = True
                                    self.create_cards()
                                self.last_killed_hp = monster.max_hp
                                self.monsters.remove(monster)

                for boss in self.bosses[:]:
                    if boss not in bomb.hit_monsters:
                        if self.check_bomb_hit(bomb, boss):
                            bomb.hit_monsters.append(boss)
                            damage = bomb.damage
                            if boss.take_damage(damage):
                                exp_gained = 100 * get_exp_multiplier(self.game_time)
                                if self.player.gain_exp(exp_gained, 1):
                                    self.leveling_up = True
                                    self.create_cards()
                                self.last_killed_hp = boss.max_hp
                                self.bosses.remove(boss)

                for ranged_monster in self.ranged_monsters[:]:
                    if ranged_monster not in bomb.hit_monsters:
                        if self.check_bomb_hit(bomb, ranged_monster):
                            bomb.hit_monsters.append(ranged_monster)
                            damage = bomb.damage
                            if ranged_monster.take_damage(damage):
                                exp_gained = 20 * get_exp_multiplier(self.game_time)
                                if self.player.gain_exp(exp_gained, 1):
                                    self.leveling_up = True
                                    self.create_cards()
                                self.last_killed_hp = ranged_monster.max_hp
                                self.ranged_monsters.remove(ranged_monster)

        for explosion in self.explosions[:]:
            explosion.update(dt)

            if not explosion.alive:
                self.explosions.remove(explosion)
                continue

            for monster in self.monsters[:]:
                if monster not in explosion.hit_monsters:
                    dx = monster.x - explosion.x
                    dy = monster.y - explosion.y
                    distance = math.sqrt(dx * dx + dy * dy)
                    if distance < explosion.max_radius + monster.radius:
                        explosion.hit_monsters.append(monster)
                        damage = explosion.damage
                        if monster.take_damage(damage):
                            exp_gained = 20 * get_exp_multiplier(self.game_time)
                            if self.player.gain_exp(exp_gained, 1):
                                self.leveling_up = True
                                self.create_cards()
                            self.last_killed_hp = monster.max_hp
                            self.monsters.remove(monster)

            for boss in self.bosses[:]:
                if boss not in explosion.hit_monsters:
                    dx = boss.x - explosion.x
                    dy = boss.y - explosion.y
                    distance = math.sqrt(dx * dx + dy * dy)
                    if distance < explosion.max_radius + boss.radius:
                        explosion.hit_monsters.append(boss)
                        damage = explosion.damage
                        if boss.take_damage(damage):
                            exp_gained = 100 * get_exp_multiplier(self.game_time)
                            if self.player.gain_exp(exp_gained, 1):
                                self.leveling_up = True
                                self.create_cards()
                            self.last_killed_hp = boss.max_hp
                            self.bosses.remove(boss)

            for ranged_monster in self.ranged_monsters[:]:
                if ranged_monster not in explosion.hit_monsters:
                    dx = ranged_monster.x - explosion.x
                    dy = ranged_monster.y - explosion.y
                    distance = math.sqrt(dx * dx + dy * dy)
                    if distance < explosion.max_radius + ranged_monster.radius:
                        explosion.hit_monsters.append(ranged_monster)
                        damage = explosion.damage
                        if ranged_monster.take_damage(damage):
                            exp_gained = 20 * get_exp_multiplier(self.game_time)
                            if self.player.gain_exp(exp_gained, 1):
                                self.leveling_up = True
                                self.create_cards()
                            self.last_killed_hp = ranged_monster.max_hp
                            self.ranged_monsters.remove(ranged_monster)

        for molotov in self.molotovs[:]:
            molotov.update(dt)

            if molotov.landed:
                puddle = FirePuddle(molotov.x, molotov.y, molotov.damage, molotov.duration, molotov.radius)
                self.fire_puddles.append(puddle)
                molotov.alive = False

            if not molotov.alive:
                self.molotovs.remove(molotov)

        for fire_puddle in self.fire_puddles[:]:
            fire_puddle.update(dt)

            if not fire_puddle.alive:
                self.fire_puddles.remove(fire_puddle)
                continue

            if fire_puddle.should_damage():
                for monster in self.monsters[:]:
                    if monster not in fire_puddle.hit_monsters_this_tick:
                        dx = monster.x - fire_puddle.x
                        dy = monster.y - fire_puddle.y
                        distance = math.sqrt(dx * dx + dy * dy)
                        if distance <= fire_puddle.radius:
                            fire_puddle.hit_monsters_this_tick.append(monster)
                            if monster.take_damage(fire_puddle.damage):
                                exp_gained = 20 * get_exp_multiplier(self.game_time)
                                if self.player.gain_exp(exp_gained, 1):
                                    self.leveling_up = True
                                    self.create_cards()
                                self.last_killed_hp = monster.max_hp
                                self.monsters.remove(monster)

                for ranged_monster in self.ranged_monsters[:]:
                    if ranged_monster not in fire_puddle.hit_monsters_this_tick:
                        dx = ranged_monster.x - fire_puddle.x
                        dy = ranged_monster.y - fire_puddle.y
                        distance = math.sqrt(dx * dx + dy * dy)
                        if distance <= fire_puddle.radius:
                            fire_puddle.hit_monsters_this_tick.append(ranged_monster)
                            if ranged_monster.take_damage(fire_puddle.damage):
                                exp_gained = 20 * get_exp_multiplier(self.game_time)
                                if self.player.gain_exp(exp_gained, 1):
                                    self.leveling_up = True
                                    self.create_cards()
                                self.last_killed_hp = ranged_monster.max_hp
                                self.ranged_monsters.remove(ranged_monster)

                for boss in self.bosses[:]:
                    if boss not in fire_puddle.hit_monsters_this_tick:
                        dx = boss.x - fire_puddle.x
                        dy = boss.y - fire_puddle.y
                        distance = math.sqrt(dx * dx + dy * dy)
                        if distance <= fire_puddle.radius:
                            fire_puddle.hit_monsters_this_tick.append(boss)
                            if boss.take_damage(fire_puddle.damage):
                                exp_gained = 100 * get_exp_multiplier(self.game_time)
                                if self.player.gain_exp(exp_gained, 1):
                                    self.leveling_up = True
                                    self.create_cards()
                                self.last_killed_hp = boss.max_hp
                                self.bosses.remove(boss)

        for ice in self.ice_cones[:]:
            ice.update(dt)

            if not ice.alive:
                self.ice_cones.remove(ice)
                continue

            for monster in self.monsters[:]:
                if monster in ice.hit_monsters:
                    continue
                dx = monster.x - ice.x
                dy = monster.y - ice.y
                distance = math.sqrt(dx * dx + dy * dy)
                if distance < ice.radius + monster.radius:
                    ice.hit_monsters.append(monster)
                    monster.apply_freeze(0.15, 3.0)
                    if monster.take_damage(ice.damage):
                        exp_gained = 20 * get_exp_multiplier(self.game_time)
                        if self.player.gain_exp(exp_gained, 1):
                            self.leveling_up = True
                            self.create_cards()
                        self.last_killed_hp = monster.max_hp
                        self.monsters.remove(monster)
                    ice.alive = False
                    break

            for boss in self.bosses[:]:
                if boss in ice.hit_monsters:
                    continue
                dx = boss.x - ice.x
                dy = boss.y - ice.y
                distance = math.sqrt(dx * dx + dy * dy)
                if distance < ice.radius + boss.radius:
                    ice.hit_monsters.append(boss)
                    boss.apply_freeze(0.15, 3.0)
                    if boss.take_damage(ice.damage):
                        exp_gained = 100 * get_exp_multiplier(self.game_time)
                        if self.player.gain_exp(exp_gained, 1):
                            self.leveling_up = True
                            self.create_cards()
                        self.last_killed_hp = boss.max_hp
                        self.bosses.remove(boss)
                    ice.alive = False
                    break

            for ranged_monster in self.ranged_monsters[:]:
                if ranged_monster in ice.hit_monsters:
                    continue
                dx = ranged_monster.x - ice.x
                dy = ranged_monster.y - ice.y
                distance = math.sqrt(dx * dx + dy * dy)
                if distance < ice.radius + ranged_monster.radius:
                    ice.hit_monsters.append(ranged_monster)
                    ranged_monster.apply_freeze(0.15, 3.0)
                    if ranged_monster.take_damage(ice.damage):
                        exp_gained = 20 * get_exp_multiplier(self.game_time)
                        if self.player.gain_exp(exp_gained, 1):
                            self.leveling_up = True
                            self.create_cards()
                        self.last_killed_hp = ranged_monster.max_hp
                        self.ranged_monsters.remove(ranged_monster)
                    ice.alive = False
                    break

        for meteor in self.meteors[:]:
            landed = meteor.update(dt)
            if landed:
                for monster in self.monsters[:]:
                    dx = monster.x - meteor.x
                    dy = monster.y - meteor.y
                    distance = math.sqrt(dx * dx + dy * dy)
                    if distance < meteor.impact_radius + monster.radius:
                        if monster.take_damage(meteor.damage):
                            exp_gained = 20 * get_exp_multiplier(self.game_time)
                            if self.player.gain_exp(exp_gained, 1):
                                self.leveling_up = True
                                self.create_cards()
                            self.last_killed_hp = monster.max_hp
                            self.monsters.remove(monster)

                for boss in self.bosses[:]:
                    dx = boss.x - meteor.x
                    dy = boss.y - meteor.y
                    distance = math.sqrt(dx * dx + dy * dy)
                    if distance < meteor.impact_radius + boss.radius:
                        if boss.take_damage(meteor.damage):
                            exp_gained = 100 * get_exp_multiplier(self.game_time)
                            if self.player.gain_exp(exp_gained, 1):
                                self.leveling_up = True
                                self.create_cards()
                            self.last_killed_hp = boss.max_hp
                            self.bosses.remove(boss)

                for ranged_monster in self.ranged_monsters[:]:
                    dx = ranged_monster.x - meteor.x
                    dy = ranged_monster.y - meteor.y
                    distance = math.sqrt(dx * dx + dy * dy)
                    if distance < meteor.impact_radius + ranged_monster.radius:
                        if ranged_monster.take_damage(meteor.damage):
                            exp_gained = 20 * get_exp_multiplier(self.game_time)
                            if self.player.gain_exp(exp_gained, 1):
                                self.leveling_up = True
                                self.create_cards()
                            self.last_killed_hp = ranged_monster.max_hp
                            self.ranged_monsters.remove(ranged_monster)

            if not meteor.alive:
                self.meteors.remove(meteor)
                continue

        for zeus_spear in self.zeus_spears[:]:
            alive = zeus_spear.update(dt, self.player.x, self.player.y)

            if not alive:
                if zeus_spear in self.zeus_spears:
                    self.zeus_spears.remove(zeus_spear)
                continue

            for monster in self.monsters[:]:
                dx = monster.x - zeus_spear.x
                dy = monster.y - zeus_spear.y
                distance = math.sqrt(dx * dx + dy * dy)

                if distance < zeus_spear.radius + monster.radius:
                    monster.zeus_marked = True
                    monster.zeus_marked_timer = 5.0

                    if monster.zeus_marked:
                        if zeus_spear.level >= 10:
                            damage_multiplier = 5
                        else:
                            damage_multiplier = 3
                    else:
                        damage_multiplier = 1

                    if monster.take_damage(zeus_spear.damage * damage_multiplier):
                        exp_gained = 20 * get_exp_multiplier(self.game_time)
                        if self.player.gain_exp(exp_gained, 1):
                            self.leveling_up = True
                            self.create_cards()
                        self.last_killed_hp = monster.max_hp
                        self.monsters.remove(monster)

                    lightning_radius = 50 + zeus_spear.level * 5
                    for other_monster in self.monsters[:]:
                        if other_monster != monster:
                            dx2 = other_monster.x - monster.x
                            dy2 = other_monster.y - monster.y
                            dist2 = math.sqrt(dx2 * dx2 + dy2 * dy2)
                            if dist2 < lightning_radius:
                                if other_monster.take_damage(zeus_spear.damage // 2):
                                    exp_gained = 20 * get_exp_multiplier(self.game_time)
                                    if self.player.gain_exp(exp_gained, 1):
                                        self.leveling_up = True
                                        self.create_cards()
                                    self.last_killed_hp = other_monster.max_hp
                                    self.monsters.remove(other_monster)

            if not zeus_spear.alive:
                if zeus_spear in self.zeus_spears:
                    self.zeus_spears.remove(zeus_spear)
                continue

        for shotgun in self.shotguns[:]:
            shotgun.update(dt)
            for bullet in shotgun.bullets[:]:
                for target in self.monsters + self.ranged_monsters + self.bosses:
                    if self.check_projectile_hit(bullet, target):
                        if target.take_damage(bullet.damage):
                            if target in self.monsters:
                                exp_gained = 20 * get_exp_multiplier(self.game_time)
                                if self.player.gain_exp(exp_gained, 1):
                                    self.leveling_up = True
                                    self.create_cards()
                                self.last_killed_hp = target.max_hp
                                self.monsters.remove(target)
                            elif target in self.ranged_monsters:
                                exp_gained = 20 * get_exp_multiplier(self.game_time)
                                if self.player.gain_exp(exp_gained, 1):
                                    self.leveling_up = True
                                    self.create_cards()
                                self.last_killed_hp = target.max_hp
                                self.ranged_monsters.remove(target)
                            elif target in self.bosses:
                                exp_gained = 100 * get_exp_multiplier(self.game_time)
                                if self.player.gain_exp(exp_gained, 1):
                                    self.leveling_up = True
                                    self.create_cards()
                                self.last_killed_hp = target.max_hp
                                self.bosses.remove(target)
                        bullet.alive = False
                        break
                if not bullet.alive:
                    shotgun.bullets.remove(bullet)
            if not shotgun.bullets:
                self.shotguns.remove(shotgun)

        for lightning in self.lightning_chains[:]:
            lightning.update(dt)

            if not lightning.alive:
                self.lightning_chains.remove(lightning)
                continue

        for orb in self.resurrection_orbs[:]:
            orb.update(dt, self.monsters, self.ranged_monsters, self.bosses, self)

            if not orb.alive:
                self.resurrection_orbs.remove(orb)
                continue

        for sword in self.rotating_swords[:]:
            sword.update(dt, self.monsters, self.ranged_monsters, self.bosses)

            if not sword.alive:
                self.rotating_swords.remove(sword)
                continue

        if self.fire_aura:
            self.fire_aura.update(dt, self.player.x, self.player.y, self.monsters, self.ranged_monsters, self.bosses, self)

        for card in self.cards:
            if self.mouse_clicked and card.check_click(self.mouse_x, self.mouse_y):
                self.apply_option(card.option_index)
                self.leveling_up = False
                self.cards = []
                self.mouse_clicked = False
                break


class GameWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game = Game()
        self.joystick = JoystickWidget()
        self.add_widget(self.joystick)

        self.attack_btn = Button(
            text="攻击",
            size=(120, 120),
            pos=(SCREEN_WIDTH - 140, 20),
            font_size=20
        )
        self.attack_btn.bind(on_press=self.on_attack_press)
        self.add_widget(self.attack_btn)

        self.pause_btn = Button(
            text="暂停",
            size=(80, 50),
            pos=(SCREEN_WIDTH - 90, SCREEN_HEIGHT - 60),
            font_size=16
        )
        self.pause_btn.bind(on_press=self.on_pause_press)
        self.add_widget(self.pause_btn)

        self.ui_layout = BoxLayout(orientation='vertical', size_hint=(None, None), pos=(10, SCREEN_HEIGHT - 150))
        self.score_label = Label(text='积分: 0', font_size=14, size_hint_y=None, height=25, color=(0, 0, 0, 1))
        self.time_label = Label(text='时间: 0s', font_size=12, size_hint_y=None, height=20, color=(0, 0, 0, 1))
        self.level_label = Label(text='等级: 1', font_size=12, size_hint_y=None, height=20, color=(0, 0, 0, 1))
        self.hp_label = Label(text='HP: 100/100', font_size=12, size_hint_y=None, height=20, color=(0, 1, 0, 1))
        self.weapon_label = Label(text='武器: 剑 Lv.1', font_size=12, size_hint_y=None, height=20, color=(1, 1, 0, 1))
        self.skill_labels = []
        self.ui_layout.add_widget(self.score_label)
        self.ui_layout.add_widget(self.time_label)
        self.ui_layout.add_widget(self.level_label)
        self.ui_layout.add_widget(self.hp_label)
        self.ui_layout.add_widget(self.weapon_label)
        self.add_widget(self.ui_layout)

        self.exp_bar = None
        self.exp_label = None

        Clock.schedule_interval(self.update, 1/60)

    def on_touch_down(self, touch):
        # 先检查是否是摇杆或按钮触摸，它们会自己处理
        if super().on_touch_down(touch):
            return True
        
        # 处理升级卡片点击
        if self.game.leveling_up:
            touch_x = touch.x - SCREEN_WIDTH // 2
            touch_y = touch.y - SCREEN_HEIGHT // 2
            for card in self.game.cards:
                if card.check_click(touch_x, touch_y):
                    self.game.apply_option(card.option_index)
                    self.game.leveling_up = False
                    self.game.cards = []
                    self.game.mouse_clicked = False
                    return True
        
        return False

    def on_attack_press(self, instance):
        if not self.game.game_over and not self.game.leveling_up:
            self.game.handle_attack()

    def on_pause_press(self, instance):
        if not self.game.game_over:
            self.game.paused = not self.game.paused
            self.pause_btn.text = "继续" if self.game.paused else "暂停"

    def update_labels(self):
        player = self.game.player
        self.score_label.text = f'积分: {int(self.game.score)}'
        self.time_label.text = f'时间: {int(self.game.game_time)}s'
        self.level_label.text = f'等级: {player.level}'
        self.hp_label.text = f'HP: {int(player.hp)}/{player.max_hp}'
        weapon_names = {"sword": "剑", "staff": "法杖", "gun": "枪", "zeus_spear": "宙斯之矛"}
        self.weapon_label.text = f'武器: {weapon_names.get(player.weapon, player.weapon)} Lv.{player.weapon_level}'

        for skill in player.skills:
            level = player.skill_levels.get(skill, 1)
            cooldown = self.game.skill_timers.get(skill, 0)
            skill_names = {"fireball": "火球术", "laser": "激光", "bomb": "炸弹", "boomerang": "回旋镖", "molotov": "燃烧瓶", "ice_cone": "冰锥", "resurrection": "秽土转生", "rotating_sword": "旋转飞剑", "fire_aura": "火焰领域"}
            skill_text = f'{skill_names.get(skill, skill)}: Lv.{level} CD:{cooldown:.1f}s'
            while len(self.skill_labels) <= list(player.skills).index(skill):
                lbl = Label(text='', font_size=10, size_hint_y=None, height=18, color=(0, 1, 1, 1), pos=(10, SCREEN_HEIGHT - 180 - len(self.skill_labels) * 20))
                self.add_widget(lbl)
                self.skill_labels.append(lbl)
            idx = list(player.skills).index(skill)
            if idx < len(self.skill_labels):
                self.skill_labels[idx].text = skill_text
                self.skill_labels[idx].pos = (10, SCREEN_HEIGHT - 180 - idx * 20)
                self.skill_labels[idx].opacity = 1

        for i in range(len(player.skills), len(self.skill_labels)):
            self.skill_labels[i].opacity = 0

        if not self.game.leveling_up:
            if hasattr(self, 'level_up_title') and self.level_up_title.parent:
                self.level_up_title.opacity = 0
            for i in range(3):
                card_label_key = f'card_label_{i}'
                if hasattr(self, card_label_key):
                    lbl = getattr(self, card_label_key)
                    if lbl and lbl.parent:
                        lbl.opacity = 0

        if not self.game.game_over:
            if hasattr(self, 'game_over_label') and self.game_over_label.parent:
                self.game_over_label.opacity = 0

        if not self.game.paused:
            if hasattr(self, 'pause_label') and self.pause_label.parent:
                self.pause_label.opacity = 0

    def update(self, dt):
        # 使用摇杆控制移动
        move_dx = self.joystick.dx * self.game.player.speed
        move_dy = self.joystick.dy * self.game.player.speed

        self.game.update(move_dx, move_dy, dt)
        self.game.mouse_x = self.game.player.x + self.joystick.dx * 100
        self.game.mouse_y = self.game.player.y + self.joystick.dy * 100
        self.game.mouse_clicked = False

        # 更新UI标签（即使暂停也更新）
        self.update_labels()
        self.canvas.clear()

        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=(0, 0), size=(SCREEN_WIDTH, SCREEN_HEIGHT))

            self.draw_fire_aura()
            self.draw_meteors()
            self.draw_player()
            self.draw_monsters()
            self.draw_ranged_monsters()
            self.draw_bosses()
            self.draw_boss_bullets()
            self.draw_ranged_bullets()
            self.draw_projectiles()
            self.draw_sword_waves()
            self.draw_lasers()
            self.draw_bombs()
            self.draw_explosions()
            self.draw_molotovs()
            self.draw_fire_puddles()
            self.draw_ice_cones()
            self.draw_zeus_spears()
            self.draw_shotguns()
            self.draw_lightning_chains()
            self.draw_resurrection_orbs()
            self.draw_rotating_swords()
            self.draw_exp_bar()

            if self.game.leveling_up:
                self.draw_level_up()
            if self.game.game_over:
                self.draw_game_over()
            if self.game.paused:
                self.draw_paused()

    def draw_fire_aura(self):
        if not self.game.fire_aura:
            return

        aura = self.game.fire_aura
        for ring in aura.rings:
            rx = ring["x"] + SCREEN_WIDTH // 2
            ry = ring["y"] + SCREEN_HEIGHT // 2
            ring_color = hex_to_rgba(aura.ring_color)
            Color(*ring_color)
            Line(circle=(rx, ry, ring["radius"]), width=aura.ring_width)

    def draw_exp_bar(self):
        player = self.game.player
        exp_bar_width = 100
        exp_bar_height = 10
        exp_ratio = player.exp / player.exp_to_level if player.exp_to_level > 0 else 0
        exp_x = 20
        exp_y = SCREEN_HEIGHT - 130

        from kivy.graphics import InstructionGroup
        self.canvas.remove_group('exp_bar')
        g = InstructionGroup()
        g.add(Color(0.5, 0.5, 0.5, 1))
        g.add(Rectangle(pos=(exp_x, exp_y), size=(exp_bar_width, exp_bar_height)))
        g.add(Color(0, 1, 0, 1))
        g.add(Rectangle(pos=(exp_x, exp_y), size=(int(exp_bar_width * exp_ratio), exp_bar_height)))
        g.group = 'exp_bar'
        self.canvas.add(g)

    def draw_meteors(self):
        for meteor in self.game.meteors:
            mx = meteor.x + SCREEN_WIDTH // 2
            my = meteor.y + SCREEN_HEIGHT // 2

            with self.canvas:
                Color(1, 0.5, 0, 1)
                Ellipse(pos=(mx - meteor.radius, my - meteor.radius),
                       size=(meteor.radius * 2, meteor.radius * 2))

    def draw_player(self):
        player = self.game.player
        x, y = player.x + SCREEN_WIDTH // 2, player.y + SCREEN_HEIGHT // 2
        angle = player.facing_angle
        facing_right = -90 < angle < 90

        head_x = x
        head_y = y + 35
        head_radius = 12

        with self.canvas:
            Color(0, 0, 0, 1)
            Line(circle=(head_x, head_y + head_radius, head_radius), width=3)

            eye_offset = 4 if facing_right else -4
            Color(0, 0, 0, 1)
            Ellipse(pos=(head_x + eye_offset - 3 - 1.5, head_y + 3 - 1.5), size=(3, 3))
            Ellipse(pos=(head_x + eye_offset + 3 - 1.5, head_y + 3 - 1.5), size=(3, 3))

            body_top = head_y - head_radius
            body_bottom = body_top - 30

            Color(0, 0, 0, 1)
            Line(points=[head_x, body_top, head_x, body_bottom], width=3)

            arm_y = body_top - 5
            arm_len = 20

            Line(points=[head_x, arm_y, head_x + arm_len * (-1 if facing_right else 1), arm_y], width=3)

            rad = math.radians(angle)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)
            Line(points=[head_x, arm_y, head_x + arm_len * cos_a, arm_y + arm_len * sin_a], width=3)

            leg_len = 20

            Line(points=[head_x, body_bottom, head_x + leg_len * math.cos(math.radians(-135)), body_bottom + leg_len * math.sin(math.radians(-135))], width=3)
            Line(points=[head_x, body_bottom, head_x + leg_len * math.cos(math.radians(-45)), body_bottom + leg_len * math.sin(math.radians(-45))], width=3)

            self.draw_weapon(x, y, angle)

    def draw_weapon(self, x, y, angle):
        player = self.game.player

        if player.weapon == "sword":
            blade_length = 50 + player.weapon_level * 5

            arm_len = 20
            arm_y = y + 35 - 12 - 5

            base_angle = angle
            rad = math.radians(angle)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)

            hand_x = x + arm_len * cos_a
            hand_y = arm_y + arm_len * sin_a

            if player.is_attacking:
                swing_progress = player.attack_timer / 0.2
                swing_offset = 60 * (1 - swing_progress)
                angle = base_angle + swing_offset
                rad = math.radians(angle)
                cos_a = math.cos(rad)
                sin_a = math.sin(rad)

            blade_end_x = hand_x + blade_length * cos_a
            blade_end_y = hand_y + blade_length * sin_a

            is_holy_sword = 5 <= player.weapon_level < 10
            is_dragon_slayer = player.weapon_level >= 10

            if is_dragon_slayer:
                Color(1, 0.55, 0, 1)
            elif is_holy_sword:
                Color(1, 0.84, 0, 1)
            else:
                Color(0.55, 0.27, 0.07, 1)

            Line(points=[hand_x, hand_y, hand_x + 15 * cos_a, hand_y + 15 * sin_a], width=4)

            if is_dragon_slayer:
                Color(1, 0.55, 0, 1)
                Line(points=[hand_x + 15 * cos_a, hand_y + 15 * sin_a, blade_end_x, blade_end_y], width=8)
            elif is_holy_sword:
                Color(1, 0.84, 0, 1)
                Line(points=[hand_x + 15 * cos_a, hand_y + 15 * sin_a, blade_end_x, blade_end_y], width=8)
            else:
                Color(0.75, 0.75, 0.75, 1)
                Line(points=[hand_x + 15 * cos_a, hand_y + 15 * sin_a, blade_end_x, blade_end_y], width=6)

            if is_dragon_slayer:
                Color(1, 0.55, 0, 1)
            elif is_holy_sword:
                Color(1, 1, 1, 1)
            else:
                Color(1, 0.84, 0, 1)
            Ellipse(pos=(blade_end_x - 3, blade_end_y - 3), size=(6, 6))

            if player.is_attacking:
                arc_radius = blade_length + 20
                if is_dragon_slayer:
                    Color(1, 0.55, 0, 0.5)
                elif is_holy_sword:
                    Color(1, 0.84, 0, 0.5)
                else:
                    Color(0, 0, 0, 0.3)

                start_rad = math.radians(base_angle - 60)
                end_rad = math.radians(base_angle + 60)
                arc_points = []
                for i in range(10):
                    t = i / 9
                    arc_angle = start_rad + t * (end_rad - start_rad)
                    arc_x = hand_x + arc_radius * math.cos(arc_angle)
                    arc_y = hand_y + arc_radius * math.sin(arc_angle)
                    arc_points.extend([arc_x, arc_y])
                Line(points=arc_points, width=2)

        elif player.weapon == "staff":
            staff_length = 60 + player.weapon_level * 3

            rad = math.radians(angle)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)

            arm_len = 20
            arm_y = y + 35 - 12 - 5
            hand_x = x + arm_len * cos_a
            hand_y = arm_y + arm_len * sin_a

            is_golden_staff = player.weapon_level >= 5

            staff_end_x = hand_x + staff_length * cos_a
            staff_end_y = hand_y + staff_length * sin_a

            if is_golden_staff:
                Color(1, 0.84, 0, 1)
            else:
                Color(0.55, 0.27, 0.07, 1)

            Line(points=[hand_x, hand_y, staff_end_x, staff_end_y], width=5)

            gem_radius = 8 + player.weapon_level
            Color(0.54, 0.17, 0.89, 1)
            Ellipse(pos=(staff_end_x - gem_radius, staff_end_y - gem_radius), size=(gem_radius * 2, gem_radius * 2))

        elif player.weapon == "gun":
            barrel_length = 35 + player.weapon_level * 2

            rad = math.radians(angle)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)

            arm_len = 20
            arm_y = y + 35 - 12 - 5
            hand_x = x + arm_len * cos_a
            hand_y = arm_y + arm_len * sin_a

            Color(0.2, 0.2, 0.2, 1)
            Line(points=[hand_x - 8 * sin_a, hand_y + 8 * cos_a, hand_x - 8 * sin_a + 25 * cos_a, hand_y + 8 * cos_a + 25 * sin_a], width=16)

            Line(points=[hand_x, hand_y - 6, hand_x + barrel_length * cos_a, hand_y - 6 + barrel_length * sin_a], width=12)

        elif player.weapon == "zeus_spear":
            if player.zeus_spear_in_hand:
                if player.weapon_level >= 10:
                    Color(1, 1, 0, 1)
                else:
                    Color(0.5, 0.8, 1, 1)

                arm_len = 20
                arm_y = y + 35 - 12 - 5

                rad = math.radians(angle)
                cos_a = math.cos(rad)
                sin_a = math.sin(rad)

                hand_x = x + arm_len * cos_a
                hand_y = arm_y + arm_len * sin_a

                spear_points = []
                p1_x, p1_y = hand_x, hand_y
                spear_points.extend([p1_x, p1_y])

                p2_x = hand_x + 15 * cos_a
                p2_y = hand_y + 15 * sin_a
                spear_points.extend([p2_x, p2_y])

                branch1_angle = math.radians(angle + 45)
                p3_x = p2_x + 8 * math.cos(branch1_angle)
                p3_y = p2_y + 8 * math.sin(branch1_angle)

                p4_angle = math.radians(angle + 45 - 90)
                p4_x = p3_x + 8 * math.cos(p4_angle)
                p4_y = p3_y + 8 * math.sin(p4_angle)

                p5_x = p4_x + 15 * cos_a
                p5_y = p4_y + 15 * sin_a

                spear_points.extend([p3_x, p3_y, p4_x, p4_y, p5_x, p5_y])

                Line(points=spear_points, width=3)

                Color(1, 1, 0, 1)
                branch2_angle = math.radians(angle + 30)
                b2_x = p2_x + 5 * math.cos(branch2_angle)
                b2_y = p2_y + 5 * math.sin(branch2_angle)
                Line(points=[p2_x, p2_y, b2_x, b2_y], width=2)

                branch3_angle = math.radians(angle - 30)
                b3_x = p2_x + 5 * math.cos(branch3_angle)
                b3_y = p2_y + 5 * math.sin(branch3_angle)
                Line(points=[p2_x, p2_y, b3_x, b3_y], width=2)

    def draw_monsters(self):
        for monster in self.game.monsters:
            mx = monster.x + SCREEN_WIDTH // 2
            my = monster.y + SCREEN_HEIGHT // 2

            display_color = hex_to_rgba(monster.color)
            if monster.zeus_marked:
                display_color = hex_to_rgba("#9932CC")
            elif monster.frozen_timer > 0:
                display_color = hex_to_rgba("#00BFFF")
            elif monster.slow_timer > 0:
                display_color = hex_to_rgba("#87CEEB")

            with self.canvas:
                Color(*display_color)
                Ellipse(pos=(mx - monster.radius, my - monster.radius), size=(monster.radius * 2, monster.radius * 2))

                ring_color = hex_to_rgba(monster.ring_color)
                Color(*ring_color)
                Line(circle=(mx, my, monster.radius + 2), width=1)

    def draw_ranged_monsters(self):
        for monster in self.game.ranged_monsters:
            mx = monster.x + SCREEN_WIDTH // 2
            my = monster.y + SCREEN_HEIGHT // 2

            display_color = hex_to_rgba("#4169E1")
            if monster.zeus_marked:
                display_color = hex_to_rgba("#9932CC")
            elif monster.frozen_timer > 0:
                display_color = hex_to_rgba("#00BFFF")
            elif monster.slow_timer > 0:
                display_color = hex_to_rgba("#87CEEB")

            with self.canvas:
                Color(*display_color)
                Ellipse(pos=(mx - monster.radius, my - monster.radius), size=(monster.radius * 2, monster.radius * 2))

                Color(0, 0, 0.5, 1)
                Line(circle=(mx, my, monster.radius + 2), width=1)

    def draw_bosses(self):
        for boss in self.game.bosses:
            bx = boss.x + SCREEN_WIDTH // 2
            by = boss.y + SCREEN_HEIGHT // 2

            display_color = hex_to_rgba("#8B0000")
            if boss.zeus_marked:
                display_color = hex_to_rgba("#9932CC")
            elif boss.frozen_timer > 0:
                display_color = hex_to_rgba("#00BFFF")
            elif boss.slow_timer > 0:
                display_color = hex_to_rgba("#87CEEB")

            with self.canvas:
                Color(*display_color)
                Ellipse(pos=(bx - boss.radius, by - boss.radius), size=(boss.radius * 2, boss.radius * 2))

                Color(0.5, 0, 0, 1)
                Line(circle=(bx, by, boss.radius + 3), width=2)

    def draw_boss_bullets(self):
        for bullet in self.game.boss_bullets:
            bx = bullet.x + SCREEN_WIDTH // 2
            by = bullet.y + SCREEN_HEIGHT // 2

            with self.canvas:
                Color(1, 0, 0, 1)
                Ellipse(pos=(bx - bullet.radius, by - bullet.radius), size=(bullet.radius * 2, bullet.radius * 2))

    def draw_ranged_bullets(self):
        for bullet in self.game.ranged_bullets:
            bx = bullet.x + SCREEN_WIDTH // 2
            by = bullet.y + SCREEN_HEIGHT // 2

            with self.canvas:
                Color(0, 0, 1, 1)
                Ellipse(pos=(bx - bullet.radius, by - bullet.radius), size=(bullet.radius * 2, bullet.radius * 2))

    def draw_projectiles(self):
        for proj in self.game.projectiles:
            px = proj.x + SCREEN_WIDTH // 2
            py = proj.y + SCREEN_HEIGHT // 2

            with self.canvas:
                if proj.proj_type == "fireball":
                    Color(1, 0.5, 0, 1)
                    Ellipse(pos=(px - proj.radius, py - proj.radius), size=(proj.radius * 2, proj.radius * 2))
                    Color(1, 1, 0, 1)
                    Ellipse(pos=(px - proj.radius + 2, py - proj.radius + 2), size=(proj.radius * 2 - 4, proj.radius * 2 - 4))
                elif proj.proj_type == "boomerang":
                    Color(0, 1, 1, 1)
                    Ellipse(pos=(px - 10, py - 4), size=(20, 8))
                elif proj.proj_type == "gun_bullet" or proj.proj_type == "sniper_bullet":
                    Color(1, 1, 0, 1)
                    Ellipse(pos=(px - proj.radius, py - proj.radius), size=(proj.radius * 2, proj.radius * 2))
                else:
                    Color(0.5, 0.5, 0.5, 1)
                    Ellipse(pos=(px - proj.radius, py - proj.radius), size=(proj.radius * 2, proj.radius * 2))

    def draw_sword_waves(self):
        for wave in self.game.sword_waves:
            wx = wave.x + SCREEN_WIDTH // 2
            wy = wave.y + SCREEN_HEIGHT // 2

            if wave.is_ultimate:
                color = (1, 0.55, 0, 1)
            else:
                color = (1, 1, 1, 1)

            with self.canvas:
                Color(*color)
                rad = math.radians(wave.angle)
                cos_a = math.cos(rad)
                sin_a = math.sin(rad)

                wave_length = 40
                wave_width = 15

                cx = wx
                cy = wy

                p1x = cx - wave_width * sin_a
                p1y = cy + wave_width * cos_a
                p2x = cx + wave_length * cos_a - wave_width * sin_a * 0.3
                p2y = cy + wave_length * sin_a + wave_width * cos_a * 0.3
                p3x = cx + wave_length * cos_a + wave_width * sin_a * 0.3
                p3y = cy + wave_length * sin_a - wave_width * cos_a * 0.3
                p4x = cx + wave_width * sin_a
                p4y = cy - wave_width * cos_a

                Line(points=[p1x, p1y, p2x, p2y, p3x, p3y, p4x, p4y], width=3)

    def draw_lasers(self):
        for laser in self.game.lasers:
            with self.canvas:
                Color(1, 0, 1, 1)
                for seg in laser.segments:
                    x1, y1, x2, y2 = seg
                    Line(points=[x1 + SCREEN_WIDTH // 2, y1 + SCREEN_HEIGHT // 2,
                                x2 + SCREEN_WIDTH // 2, y2 + SCREEN_HEIGHT // 2], width=3)

    def draw_bombs(self):
        for bomb in self.game.bombs:
            bx = bomb.x + SCREEN_WIDTH // 2
            by = bomb.y + SCREEN_HEIGHT // 2

            with self.canvas:
                if bomb.exploding:
                    progress = 1.0 - (bomb.explosion_time / 0.3)
                    current_radius = int(bomb.explosion_radius * progress)
                    Color(1, 0.5, 0, 1)
                    Ellipse(pos=(bx - current_radius, by - current_radius),
                           size=(current_radius * 2, current_radius * 2))
                else:
                    Color(0.3, 0.3, 0.3, 1)
                    Ellipse(pos=(bx - 10, by - 10), size=(20, 20))

    def draw_explosions(self):
        for explosion in self.game.explosions:
            ex = explosion.x + SCREEN_WIDTH // 2
            ey = explosion.y + SCREEN_HEIGHT // 2

            progress = 1.0 - (explosion.lifetime / 0.3)
            current_radius = int(explosion.radius * progress)

            with self.canvas:
                Color(1, 0.5, 0, 0.8)
                Ellipse(pos=(ex - current_radius, ey - current_radius),
                       size=(current_radius * 2, current_radius * 2))

    def draw_molotovs(self):
        for molotov in self.game.molotovs:
            mx = molotov.x + SCREEN_WIDTH // 2
            my = molotov.y + SCREEN_HEIGHT // 2

            with self.canvas:
                Color(0.5, 0, 0, 1)
                Ellipse(pos=(mx - 5, my - 5), size=(10, 10))

    def draw_fire_puddles(self):
        for puddle in self.game.fire_puddles:
            px = puddle.x + SCREEN_WIDTH // 2
            py = puddle.y + SCREEN_HEIGHT // 2

            with self.canvas:
                Color(1, 0.3, 0, 0.7)
                Ellipse(pos=(px - puddle.radius, py - puddle.radius),
                       size=(puddle.radius * 2, puddle.radius * 2))

    def draw_ice_cones(self):
        for ice in self.game.ice_cones:
            ix = ice.x + SCREEN_WIDTH // 2
            iy = ice.y + SCREEN_HEIGHT // 2

            with self.canvas:
                Color(0, 0.8, 1, 1)

                rad = math.radians(ice.angle)
                cos_a = math.cos(rad)
                sin_a = math.sin(rad)

                tip_x = ix + 20 * cos_a
                tip_y = iy + 20 * sin_a

                base1_x = ix + 8 * cos_a - 8 * sin_a
                base1_y = iy + 20 * sin_a + 8 * cos_a
                base2_x = ix + 8 * cos_a + 8 * sin_a
                base2_y = iy + 20 * sin_a - 8 * cos_a

                Line(points=[tip_x, tip_y, base1_x, base1_y, base2_x, base2_y, tip_x, tip_y], width=2)

    def draw_zeus_spears(self):
        for spear in self.game.zeus_spears:
            sx = spear.x + SCREEN_WIDTH // 2
            sy = spear.y + SCREEN_HEIGHT // 2

            angle = spear.get_direction()
            rad = math.radians(angle)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)

            with self.canvas:
                Color(1, 1, 0, 1)
                Line(points=[sx - 15 * cos_a, sy - 15 * sin_a,
                            sx + 15 * cos_a, sy + 15 * sin_a], width=3)

    def draw_shotguns(self):
        for shotgun in self.game.shotguns:
            for bullet in shotgun.bullets:
                bx = bullet.x + SCREEN_WIDTH // 2
                by = bullet.y + SCREEN_HEIGHT // 2

                with self.canvas:
                    Color(1, 1, 0, 1)
                    Ellipse(pos=(bx - bullet.radius, by - bullet.radius),
                           size=(bullet.radius * 2, bullet.radius * 2))

    def draw_lightning_chains(self):
        for chain in self.game.lightning_chains:
            with self.canvas:
                Color(0.5, 0, 1, 1)
                prev_x = chain.start_x + SCREEN_WIDTH // 2
                prev_y = chain.start_y + SCREEN_HEIGHT // 2
                for target in chain.targets:
                    target_x = target.x + SCREEN_WIDTH // 2
                    target_y = target.y + SCREEN_HEIGHT // 2
                    Line(points=[prev_x, prev_y, target_x, target_y], width=2)
                    prev_x = target_x
                    prev_y = target_y

    def draw_resurrection_orbs(self):
        for orb in self.game.resurrection_orbs:
            ox = orb.x + SCREEN_WIDTH // 2
            oy = orb.y + SCREEN_HEIGHT // 2

            with self.canvas:
                Color(0, 1, 0, 1)
                Ellipse(pos=(ox - orb.radius, oy - orb.radius),
                       size=(orb.radius * 2, orb.radius * 2))

                Color(0.5, 1, 0.5, 1)
                Ellipse(pos=(ox - orb.radius * 0.6, oy - orb.radius * 0.6),
                       size=(orb.radius * 1.2, orb.radius * 1.2))

    def draw_rotating_swords(self):
        for sword in self.game.rotating_swords:
            sx = sword.x + SCREEN_WIDTH // 2
            sy = sword.y + SCREEN_HEIGHT // 2

            with self.canvas:
                Color(0.27, 0.51, 0.71, 1)

                rad = math.radians(sword.angle)
                cos_a = math.cos(rad)
                sin_a = math.sin(rad)

                blade_length = 30 + sword.level * 2
                end_x = sx + blade_length * cos_a
                end_y = sy + blade_length * sin_a

                Line(points=[sx, sy, end_x, end_y], width=4 + int(sword.level * 0.2))

                Color(1, 0.84, 0, 1)
                Ellipse(pos=(end_x - 3, end_y - 3), size=(6, 6))

    def draw_ui(self):
        player = self.game.player

        self.score_label.text = f'积分: {int(self.game.score)}'
        self.time_label.text = f'时间: {int(self.game.game_time)}s'
        self.level_label.text = f'等级: {player.level}'
        self.hp_label.text = f'HP: {int(player.hp)}/{player.max_hp}'

        weapon_names = {"sword": "剑", "staff": "法杖", "gun": "枪", "zeus_spear": "宙斯之矛"}
        self.weapon_label.text = f'武器: {weapon_names.get(player.weapon, player.weapon)} Lv.{player.weapon_level}'

        self.canvas.remove_group('exp_bar')
        exp_bar_width = 100
        exp_bar_height = 10
        exp_ratio = player.exp / player.exp_to_level if player.exp_to_level > 0 else 0

        exp_x = 20
        exp_y = SCREEN_HEIGHT - 130

        from kivy.graphics import InstructionGroup
        g = InstructionGroup()
        g.add(Color(0.5, 0.5, 0.5, 1))
        g.add(Rectangle(pos=(exp_x, exp_y), size=(exp_bar_width, exp_bar_height)))
        g.add(Color(0, 1, 0, 1))
        g.add(Rectangle(pos=(exp_x, exp_y), size=(int(exp_bar_width * exp_ratio), exp_bar_height)))
        g.group = 'exp_bar'
        self.canvas.add(g)

        skill_y = SCREEN_HEIGHT - 180
        for skill in player.skills:
            level = player.skill_levels.get(skill, 1)
            cooldown = self.game.skill_timers.get(skill, 0)
            skill_names = {"fireball": "火球术", "laser": "激光", "bomb": "炸弹", "boomerang": "回旋镖", "molotov": "燃烧瓶", "ice_cone": "冰锥", "resurrection": "秽土转生", "rotating_sword": "旋转飞剑", "fire_aura": "火焰领域"}
            skill_text = f'{skill_names.get(skill, skill)}: Lv.{level} CD:{cooldown:.1f}s'
            while len(self.skill_labels) <= list(player.skills).index(skill):
                lbl = Label(text='', font_size=10, size_hint_y=None, height=18, color=(0, 1, 1, 1), pos=(10, skill_y - len(self.skill_labels) * 20))
                self.add_widget(lbl)
                self.skill_labels.append(lbl)
            idx = list(player.skills).index(skill)
            if idx < len(self.skill_labels):
                self.skill_labels[idx].text = skill_text
                self.skill_labels[idx].pos = (10, SCREEN_HEIGHT - 180 - idx * 20)
                self.skill_labels[idx].opacity = 1

        for i in range(len(player.skills), len(self.skill_labels)):
            self.skill_labels[i].opacity = 0

        # 隐藏升级界面标签
        if not self.game.leveling_up:
            if hasattr(self, 'level_up_title') and self.level_up_title.parent:
                self.level_up_title.opacity = 0
            for i in range(3):  # 最多3张卡片
                card_label_key = f'card_label_{i}'
                if hasattr(self, card_label_key):
                    lbl = getattr(self, card_label_key)
                    if lbl and lbl.parent:
                        lbl.opacity = 0

        # 隐藏游戏结束标签
        if not self.game.game_over:
            if hasattr(self, 'game_over_label') and self.game_over_label.parent:
                self.game_over_label.opacity = 0

        # 隐藏暂停标签
        if not self.game.paused:
            if hasattr(self, 'pause_label') and self.pause_label.parent:
                self.pause_label.opacity = 0

    def draw_level_up(self):
        with self.canvas:
            Color(0, 0, 0, 0.7)
            Rectangle(pos=(0, 0), size=(SCREEN_WIDTH, SCREEN_HEIGHT))

        if not hasattr(self, 'level_up_title') or not self.level_up_title.parent:
            self.level_up_title = Label(text='选择升级!', font_size=24, bold=True, color=(1, 1, 0, 1),
                                        size_hint=(None, None), size=(200, 40),
                                        pos=(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 50))
            self.add_widget(self.level_up_title)
        else:
            self.level_up_title.opacity = 1

        card_width = 150
        card_height = 200
        for i, card in enumerate(self.game.cards):
            cx = card.x + SCREEN_WIDTH // 2
            cy = card.y + SCREEN_HEIGHT // 2

            with self.canvas:
                Color(0.2, 0.2, 0.2, 1)
                Rectangle(pos=(cx - card_width // 2, cy - card_height // 2),
                         size=(card_width, card_height))

                Color(1, 1, 0, 1)
                Line(points=[cx - card_width // 2, cy - card_height // 2,
                            cx + card_width // 2, cy - card_height // 2,
                            cx + card_width // 2, cy + card_height // 2,
                            cx - card_width // 2, cy + card_height // 2,
                            cx - card_width // 2, cy - card_height // 2], width=2)

            card_label_key = f'card_label_{i}'
            if not hasattr(self, card_label_key) or getattr(self, card_label_key) is None or not getattr(self, card_label_key).parent:
                card_lbl = Label(text=card.option_text, font_size=9, color=(1, 1, 1, 1),
                                size_hint=(None, None), size=(card_width - 10, card_height - 20),
                                pos=(cx - card_width // 2 + 5, cy - card_height // 2 + 10),
                                text_size=(card_width - 20, card_height - 20))
                setattr(self, card_label_key, card_lbl)
                self.add_widget(card_lbl)
            else:
                lbl = getattr(self, card_label_key)
                lbl.text = card.option_text
                lbl.pos = (cx - card_width // 2 + 5, cy - card_height // 2 + 10)
                lbl.opacity = 1

    def draw_paused(self):
        with self.canvas:
            Color(0, 0, 0, 0.5)
            Rectangle(pos=(0, 0), size=(SCREEN_WIDTH, SCREEN_HEIGHT))

        if not hasattr(self, 'pause_label') or not self.pause_label.parent:
            self.pause_label = Label(text='已暂停', font_size=32, bold=True, color=(1, 1, 0, 1),
                                     size_hint=(None, None), size=(200, 50),
                                     pos=(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 20))
            self.add_widget(self.pause_label)
        else:
            self.pause_label.opacity = 1

    def draw_game_over(self):
        with self.canvas:
            Color(0, 0, 0, 0.8)
            Rectangle(pos=(0, 0), size=(SCREEN_WIDTH, SCREEN_HEIGHT))

        if not hasattr(self, 'game_over_label') or not self.game_over_label.parent:
            self.game_over_label = Label(text='游戏结束', font_size=32, bold=True, color=(1, 0, 0, 1),
                                         size_hint=(None, None), size=(250, 50),
                                         pos=(SCREEN_WIDTH // 2 - 125, SCREEN_HEIGHT // 2 + 20))
            self.add_widget(self.game_over_label)
        else:
            self.game_over_label.opacity = 1


class RoguelikeApp(App):
    def build(self):
        return GameWidget()


if __name__ == '__main__':
    RoguelikeApp().run()
