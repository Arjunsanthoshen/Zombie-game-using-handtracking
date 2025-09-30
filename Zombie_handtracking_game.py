import pygame
import random
import math
import cv2
import mediapipe as mp
import logging
import os
import sys
from pygame import mixer
import numpy as np

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BRIGHT_GREEN = (0, 255, 128)
DARK_GREEN = (0, 128, 0)
GRAY = (128, 128, 128)
DARK_PURPLE = (64, 0, 64)
PURPLE = (128, 0, 128)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
ORANGE = (255, 165, 0)

# Get screen dimensions for full screen
pygame.init()
screen_info = pygame.display.Info()
width = screen_info.current_w
height = screen_info.current_h
player_size = 40
player_speed = 5
weapon_cooldowns = {"pistol": 500, "smg": 100, "machine_gun": 200, "rocket": 1500, "flamethrower": 50}
weapon_damage = {"pistol": 1, "smg": 1, "machine_gun": 2, "rocket": 20, "flamethrower": 2}
weapon_ammo_max = {"pistol": float('inf'), "smg": 50, "machine_gun": 60, "rocket": 2, "flamethrower": 100}
weapon_range = {"pistol": 60, "smg": 30, "machine_gun": 90, "rocket": 60, "flamethrower": 20}
shield_size = 20
camera_width = 320
camera_height = 240
playable_width = width - camera_width  # Still used for initial positioning and UI
playable_height = height - camera_height  # Still used for initial positioning
barricade_size = 50

class Bullet:
    def __init__(self, x, y, target_x, target_y, weapon_type):
        self.pos = [x, y]
        dx = target_x - x
        dy = target_y - y
        dist = max(1, math.sqrt(dx*dx + dy*dy))
        speed = 10 if weapon_type != "rocket" else 5
        self.velocity = [dx/dist * speed, dy/dist * speed] if weapon_type != "flamethrower" else [dx/dist * 5, dy/dist * 5]
        self.size = 12 if weapon_type == "rocket" else 8 if weapon_type != "flamethrower" else 6
        self.life = weapon_range[weapon_type]
        self.type = weapon_type
        self.damage = weapon_damage[weapon_type]

    def update(self, barricades):
        self.pos[0] += self.velocity[0]
        self.pos[1] += self.velocity[1]
        self.life -= 1
        for barricade in barricades:
            if (barricade.pos[0] - barricade_size//2 < self.pos[0] < barricade.pos[0] + barricade_size//2 and
                barricade.pos[1] - barricade_size//2 < self.pos[1] < barricade.pos[1] + barricade_size//2):
                return True
        return self.life <= 0 or self.is_out_of_bounds()

    def is_out_of_bounds(self):
        return (self.pos[0] < 0 or self.pos[0] > width or self.pos[1] < 0 or self.pos[1] > height)

    def draw(self, surface):
        color = YELLOW if self.type == "rocket" else ORANGE if self.type == "flamethrower" else WHITE
        if self.type == "flamethrower":
            pygame.draw.circle(surface, color, [int(self.pos[0]), int(self.pos[1])], self.size)
            pygame.draw.circle(surface, YELLOW, [int(self.pos[0]), int(self.pos[1])], self.size // 2)
        else:
            pygame.draw.rect(surface, color, 
                            [self.pos[0] - self.size//2, self.pos[1] - self.size//2, self.size, self.size])
            pygame.draw.rect(surface, RED, 
                            [self.pos[0] - self.size//4, self.pos[1] - self.size//4, self.size//2, self.size//2])

class Zombie:
    def __init__(self, zombie_type="normal"):
        edge = random.randint(0, 3)
        if edge == 0: self.pos = [random.randint(0, width), -20]
        elif edge == 1: self.pos = [width + 20, random.randint(0, height)]
        elif edge == 2: self.pos = [random.randint(0, width), height + 20]
        else: self.pos = [-20, random.randint(0, height)]
        
        self.type = zombie_type
        self.spawn_time = pygame.time.get_ticks()
        if zombie_type == "fast":
            self.size = 25
            self.speed = random.uniform(1.2, 1.8)
            self.health = 1
            self.color = ORANGE
        elif zombie_type == "strong":
            self.size = 50
            self.speed = random.uniform(0.4, 0.8)
            self.health = 5
            self.color = DARK_GREEN
        elif zombie_type == "exploding":
            self.size = 40
            self.speed = random.uniform(1.5, 2.0)
            self.health = 2
            self.color = RED
        elif zombie_type == "boss":
            self.size = 80
            self.speed = 0.6
            self.health = 20
            self.color = PURPLE
        else:  # normal
            self.size = random.randint(30, 50)
            self.speed = random.uniform(0.6, 1.0)
            self.health = 2
            self.color = BRIGHT_GREEN
        self.last_hit_time = 0
        self.hit_flash = False

    def update(self, player_pos, level):
        dx = player_pos[0] - self.pos[0]
        dy = player_pos[1] - self.pos[1]
        dist = math.sqrt(dx*dx + dy*dy)
        adjusted_speed = self.speed + (level * 0.03 if self.type != "boss" else 0)
        if dist > 0:
            self.pos[0] += (dx / dist) * adjusted_speed
            self.pos[1] += (dy / dist) * adjusted_speed
        if self.pos[0] > width - self.size//2:
            self.pos[0] = width - self.size//2
        if self.pos[1] > height - self.size//2:
            self.pos[1] = height - self.size//2
        if self.pos[0] < self.size//2:
            self.pos[0] = self.size//2
        if self.pos[1] < self.size//2:
            self.pos[1] = self.size//2
        if pygame.time.get_ticks() - self.last_hit_time < 150:
            self.hit_flash = True
        else:
            self.hit_flash = False
        if pygame.time.get_ticks() - self.spawn_time > 10000 and self.type == "normal":
            self.type = "strong"
            self.size = 50
            self.speed = random.uniform(0.4, 0.8)
            self.health = 5
            self.color = DARK_GREEN

    def hit(self, damage):
        self.health -= damage
        self.last_hit_time = pygame.time.get_ticks()
        return self.health <= 0

    def explode(self, zombies, player_pos, player_health, player_shield, explosions):
        if self.type == "exploding":
            explosions.append({"pos": self.pos.copy(), "life": 20, "radius": 0, "max_radius": 100})
            for zombie in zombies[:]:
                dx = zombie.pos[0] - self.pos[0]
                dy = zombie.pos[1] - self.pos[1]
                dist = math.sqrt(dx*dx + dy*dy)
                if dist < 100 and zombie != self:
                    zombie.hit(5)
            dx = player_pos[0] - self.pos[0]
            dy = player_pos[1] - self.pos[1]
            dist = math.sqrt(dx*dx + dy*dy)
            if dist < 100:
                damage = 15
                if player_shield > 0:
                    player_shield -= damage
                    if player_shield < 0:
                        player_health += player_shield
                        player_shield = 0
                else:
                    player_health -= damage
        return player_health, player_shield

    def draw(self, surface):
        color = RED if self.hit_flash else self.color
        x, y = int(self.pos[0]), int(self.pos[1])
        pygame.draw.rect(surface, color, [x - self.size//2, y - self.size//2, self.size, self.size])
        pygame.draw.rect(surface, WHITE, [x - self.size//2, y - self.size//2, self.size, self.size], 2)
        eye_size = max(2, self.size // 10)
        eye_offset = self.size // 4
        pygame.draw.rect(surface, RED, [x - eye_offset - eye_size//2, y - eye_offset, eye_size, eye_size])
        pygame.draw.rect(surface, RED, [x + eye_offset - eye_size//2, y - eye_offset, eye_size, eye_size])
        mouth_width = self.size // 3
        pygame.draw.rect(surface, BLACK, [x - mouth_width//2, y + eye_offset, mouth_width, eye_size])

class ShieldPickup:
    def __init__(self):
        self.pos = [random.randint(shield_size, width - shield_size), 
                   random.randint(shield_size, height - shield_size)]
        self.size = shield_size
        self.value = 20

    def draw(self, surface):
        pygame.draw.circle(surface, BLUE, [int(self.pos[0]), int(self.pos[1])], self.size // 2)
        pygame.draw.circle(surface, WHITE, [int(self.pos[0]), int(self.pos[1])], self.size // 4)
        font = pygame.font.SysFont("consolas", 12)
        label = font.render("shield", True, WHITE)
        label_y = self.pos[1] + self.size//2 + 5
        if label_y < 90:  # Avoid overlapping with player stats
            label_y = 90
        surface.blit(label, [self.pos[0] - label.get_width()//2, label_y])

class AmmoPickup:
    def __init__(self):
        self.pos = [random.randint(shield_size, width - shield_size), 
                   random.randint(shield_size, height - shield_size)]
        self.size = shield_size
        self.value = {"smg": 20, "machine_gun": 30, "rocket": 1, "flamethrower": 50}

    def draw(self, surface):
        pygame.draw.circle(surface, YELLOW, [int(self.pos[0]), int(self.pos[1])], self.size // 2)
        pygame.draw.circle(surface, BLACK, [int(self.pos[0]), int(self.pos[1])], self.size // 4)
        font = pygame.font.SysFont("consolas", 12)
        label = font.render("ammo", True, WHITE)
        label_y = self.pos[1] + self.size//2 + 5
        if label_y < 90:  # Avoid overlapping with player stats
            label_y = 90
        surface.blit(label, [self.pos[0] - label.get_width()//2, label_y])

class HealthKit:
    def __init__(self):
        self.pos = [random.randint(shield_size, width - shield_size), 
                   random.randint(shield_size, height - shield_size)]
        self.size = shield_size
        self.value = 25

    def draw(self, surface):
        pygame.draw.circle(surface, RED, [int(self.pos[0]), int(self.pos[1])], self.size // 2)
        pygame.draw.circle(surface, WHITE, [int(self.pos[0]), int(self.pos[1])], self.size // 4)
        font = pygame.font.SysFont("consolas", 12)
        label = font.render("health", True, WHITE)
        label_y = self.pos[1] + self.size//2 + 5
        if label_y < 90:  # Avoid overlapping with player stats
            label_y = 90
        surface.blit(label, [self.pos[0] - label.get_width()//2, label_y])

class Barricade:
    def __init__(self):
        self.pos = [random.randint(barricade_size, width - barricade_size), 
                   random.randint(barricade_size, height - barricade_size)]
        self.size = barricade_size
        self.health = 50

    def hit(self, damage):
        self.health -= damage
        return self.health <= 0

    def draw(self, surface):
        pygame.draw.rect(surface, GRAY, [self.pos[0] - self.size//2, self.pos[1] - self.size//2, self.size, self.size])
        pygame.draw.rect(surface, BLACK, [self.pos[0] - self.size//2, self.pos[1] - self.size//2, self.size, self.size], 2)

def shoot(player_pos, crosshair_pos, current_weapon, bullets, shoot_sound, last_shoot_time, ammo, explosions):
    current_time = pygame.time.get_ticks()
    cooldown = weapon_cooldowns[current_weapon]
    if current_time - last_shoot_time < cooldown or ammo[current_weapon] <= 0 or crosshair_pos[0] > width or crosshair_pos[1] > height:
        return last_shoot_time, ammo
    bullet = Bullet(player_pos[0], player_pos[1], crosshair_pos[0], crosshair_pos[1], current_weapon)
    bullets.append(bullet)
    shoot_sound.play()
    ammo[current_weapon] -= 1
    return current_time, ammo

def check_collision(pos, size, obstacles):
    for obstacle in obstacles:
        dx = pos[0] - obstacle.pos[0]
        dy = pos[1] - obstacle.pos[1]
        dist = math.sqrt(dx*dx + dy*dy)
        if dist < size//2 + obstacle.size//2:
            return True
    return False

def check_bullet_zombie_collisions(bullets, zombies, score, level, zombie_death_sound, explosions, barricades):
    for bullet in bullets[:]:
        hit_something = False
        for zombie in zombies[:]:
            dx = zombie.pos[0] - bullet.pos[0]
            dy = zombie.pos[1] - bullet.pos[1]
            dist = math.sqrt(dx*dx + dy*dy)
            if dist < zombie.size//2 + bullet.size//2:
                bullets.remove(bullet)
                hit_something = True
                if bullet.type == "rocket":
                    explosions.append({"pos": bullet.pos.copy(), "life": 20, "radius": 0, "max_radius": 100})
                    for z in zombies[:]:
                        dz = math.sqrt((z.pos[0] - bullet.pos[0])**2 + (z.pos[1] - bullet.pos[1])**2)
                        if dz < 100:
                            if z.hit(bullet.damage):
                                z.explode(zombies, [0, 0], 0, 0, explosions)
                                zombies.remove(z)
                                score += 10 * level * (2 if z.type == "boss" else 1)
                                zombie_death_sound.play()
                elif bullet.type == "flamethrower":
                    zombie.hit(bullet.damage)
                    if pygame.time.get_ticks() % 500 < 60:
                        zombie.hit(1)
                elif zombie.hit(bullet.damage):
                    zombie.explode(zombies, [0, 0], 0, 0, explosions)
                    zombies.remove(zombie)
                    score += 10 * level * (2 if zombie.type == "boss" else 1)
                    zombie_death_sound.play()
                break
        if not hit_something and bullet.update(barricades):
            if bullet.type == "rocket":
                explosions.append({"pos": bullet.pos.copy(), "life": 20, "radius": 0, "max_radius": 100})
                for z in zombies[:]:
                    dz = math.sqrt((z.pos[0] - bullet.pos[0])**2 + (z.pos[1] - bullet.pos[1])**2)
                    if dz < 100:
                        if z.hit(bullet.damage):
                            z.explode(zombies, [0, 0], 0, 0, explosions)
                            zombies.remove(z)
                            score += 10 * level * (2 if z.type == "boss" else 1)
                            zombie_death_sound.play()
            bullets.remove(bullet)
    return score

def check_player_zombie_collisions(zombies, player_pos, player_health, player_shield, game_state, game_over_sound, zombie_death_sound, explosions):
    for zombie in zombies[:]:
        dx = zombie.pos[0] - player_pos[0]
        dy = zombie.pos[1] - player_pos[1]
        dist = math.sqrt(dx*dx + dy*dy)
        if dist < zombie.size//2 + player_size//2:
            damage = 30 if zombie.type == "boss" else 15
            if zombie.type == "exploding":
                player_health, player_shield = zombie.explode(zombies, player_pos, player_health, player_shield, explosions)
                zombies.remove(zombie)
                zombie_death_sound.play()
            else:
                if player_shield > 0:
                    player_shield -= damage
                    if player_shield < 0:
                        player_health += player_shield
                        player_shield = 0
                else:
                    player_health -= damage
                zombies.remove(zombie)
                zombie_death_sound.play()
            if player_health <= 0:
                game_over_sound.play()
                game_state = "game_over"
    return player_health, player_shield, game_state

def check_player_pickup_collisions(pickups, player_pos, player_shield, player_health, ammo):
    for pickup in pickups[:]:
        dx = pickup.pos[0] - player_pos[0]
        dy = pickup.pos[1] - player_pos[1]
        dist = math.sqrt(dx*dx + dy*dy)
        if dist < pickup.size//2 + player_size//2:
            if isinstance(pickup, ShieldPickup):
                player_shield += pickup.value
            elif isinstance(pickup, HealthKit):
                player_health = min(100, player_health + pickup.value)
            elif isinstance(pickup, AmmoPickup):
                for weapon in ammo:
                    if weapon != "pistol":
                        ammo[weapon] = min(weapon_ammo_max[weapon], ammo[weapon] + pickup.value.get(weapon, 0))
            pickups.remove(pickup)
    return player_shield, player_health, ammo

def get_hand_input(cap, hands, mp_hands, mp_draw, width, height, crosshair_pos, player_pos, current_weapon, last_switch_time, barricades):
    try:
        ret, frame = cap.read()
        if not ret:
            return crosshair_pos, player_pos, False, current_weapon, None
        frame = cv2.flip(frame, 1)  # Horizontal flip
        frame = cv2.resize(frame, (camera_width, camera_height))
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)
        shoot_triggered = False
        new_crosshair_pos = crosshair_pos.copy()
        new_player_pos = player_pos.copy()
        new_weapon = current_weapon
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                tip_x = int(index_tip.x * width)  # Use full width
                tip_y = int(index_tip.y * height)  # Use full height
                new_crosshair_pos = [max(10, min(width-10, tip_x)), max(10, min(height-10, tip_y))]
                
                wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
                wrist_x = int(wrist.x * width)  # Use full width
                wrist_y = int(wrist.y * height)  # Use full height
                dx = wrist_x - new_player_pos[0]
                dy = wrist_y - new_player_pos[1]
                dist = math.sqrt(dx*dx + dy*dy)
                if dist > 0:
                    move_x = (dx / dist) * min(player_speed, dist)
                    move_y = (dy / dist) * min(player_speed, dist)
                    temp_pos = [new_player_pos[0] + move_x, new_player_pos[1] + move_y]
                    if not check_collision(temp_pos, player_size, barricades):
                        new_player_pos[0] = max(player_size//2, min(width - player_size//2, temp_pos[0]))  # Full width
                        new_player_pos[1] = max(player_size//2, min(height - player_size//2, temp_pos[1]))  # Full height
                
                thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
                thumb_x = int(thumb_tip.x * camera_width)
                thumb_y = int(thumb_tip.y * camera_height)
                index_x = int(index_tip.x * camera_width)
                index_y = int(index_tip.y * camera_height)
                dist = math.sqrt((thumb_x - index_x)**2 + (thumb_y - index_y)**2)
                shoot_triggered = dist < 40  # Fixed typo here
                
                current_time = pygame.time.get_ticks()
                if current_time - last_switch_time > 5000:
                    finger_count = sum(1 for i in [mp_hands.HandLandmark.INDEX_FINGER_TIP, 
                                                  mp_hands.HandLandmark.MIDDLE_FINGER_TIP, 
                                                  mp_hands.HandLandmark.RING_FINGER_TIP, 
                                                  mp_hands.HandLandmark.PINKY_TIP] 
                                      if hand_landmarks.landmark[i].y < hand_landmarks.landmark[i-2].y)
                    if finger_count == 2: new_weapon = "smg"
                    elif finger_count == 3: new_weapon = "machine_gun"
                    elif finger_count == 4: new_weapon = "rocket"
        
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        camera_surface = pygame.surfarray.make_surface(np.rot90(frame_rgb, k=1))  # Rotate 90 degrees counterclockwise
        return new_crosshair_pos, new_player_pos, shoot_triggered, new_weapon, camera_surface
    except Exception as e:
        logging.error(f"Error in get_hand_input: {e}")
        return crosshair_pos, player_pos, False, current_weapon, None

def draw_retro_background(window):
    pygame.draw.rect(window, BLACK, [0, 0, width, height])
    # Removed gray rectangle since player can move everywhere

def draw_player(window, player_pos, game_start_time):
    pygame.draw.circle(window, WHITE, [int(player_pos[0]), int(player_pos[1])], player_size//2)
    pygame.draw.circle(window, BRIGHT_GREEN, [int(player_pos[0]), int(player_pos[1])], player_size//3)
    pygame.draw.line(window, RED, [player_pos[0], player_pos[1] - player_size//2], [player_pos[0], player_pos[1] + player_size//2], 2)
    pygame.draw.line(window, RED, [player_pos[0] - player_size//2, player_pos[1]], [player_pos[0] + player_size//2, player_pos[1]], 2)
    if pygame.time.get_ticks() - game_start_time < 2000:
        font = pygame.font.SysFont("consolas", 24)
        you_text = font.render("YOU", True, WHITE)
        window.blit(you_text, [player_pos[0] - you_text.get_width()//2, player_pos[1] + player_size//2 + 10])

def draw_menu(window, font, small_font, tiny_font, high_score, camera_surface):
    draw_retro_background(window)
    if camera_surface:
        window.blit(camera_surface, (playable_width, height - camera_height))
    title_font = pygame.font.SysFont("consolas", 64)
    title1 = title_font.render("ZOMBIE", True, RED)
    title2 = title_font.render("OUTBREAK", True, RED)
    window.blit(title1, [width//2 - title1.get_width()//2, height//4 - 40])  # Centered on full width
    window.blit(title2, [width//2 - title2.get_width()//2, height//4 + 20])  # Centered on full width
    start_button = font.render("CLICK SPACE", True, WHITE)
    window.blit(start_button, [width//2 - start_button.get_width()//2, height//2])
    instr_font = pygame.font.SysFont("consolas", 18)
    instr_title = font.render("INSTRUCTIONS", True, YELLOW)
    window.blit(instr_title, [width//2 - instr_title.get_width()//2, height//2 + 60])
    instructions = [
        "Wrist moves player",
        "Index finger aims",
        "Pinch to shoot",
        "2 fingers: SMG",
        "3 fingers: Machine Gun",
        "4 fingers: Rocket"
    ]
    for i, instr in enumerate(instructions):
        text = instr_font.render(instr, True, WHITE)
        window.blit(text, [width//2 - text.get_width()//2, height//2 + 100 + i*20])
    quit_text = pygame.font.SysFont("consolas", 36).render("Q TO EXIT", True, WHITE)
    window.blit(quit_text, [width//2 - quit_text.get_width()//2, height - 80])
    if high_score > 0:
        high_score_text = small_font.render(f"HIGH SCORE: {high_score}", True, BRIGHT_GREEN)
        window.blit(high_score_text, [width//2 - high_score_text.get_width()//2, height - 40])

def draw_game_over(window, font, small_font, score, high_score, camera_surface):
    draw_retro_background(window)
    if camera_surface:
        window.blit(camera_surface, (playable_width, height - camera_height))
    title_font = pygame.font.SysFont("consolas", 64)
    title = title_font.render("GAME OVER", True, RED)
    window.blit(title, [width//2 - title.get_width()//2, height//4])
    score_text = font.render(f"SCORE: {score}", True, WHITE)
    window.blit(score_text, [width//2 - score_text.get_width()//2, height//2 - 30])
    if score > high_score:
        new_high_text = font.render("NEW HIGH SCORE!", True, BRIGHT_GREEN)
        window.blit(new_high_text, [width//2 - new_high_text.get_width()//2, height//2 + 20])
    restart_text = font.render("PRESS SPACE TO RESTART", True, WHITE)
    quit_text = font.render("PRESS Q TO QUIT", True, WHITE)
    window.blit(restart_text, [width//2 - restart_text.get_width()//2, height - 120])
    window.blit(quit_text, [width//2 - quit_text.get_width()//2, height - 80])

def draw_game_ui(window, font, small_font, tiny_font, score, player_health, player_shield, wave_number, current_weapon, crosshair_pos, player_pos, ammo, explosions, reload_times, pickups, barricades, camera_surface, game_start_time):
    draw_retro_background(window)
    if camera_surface:
        window.blit(camera_surface, (playable_width, height - camera_height))
    score_text = font.render(f"SCORE: {score}", True, WHITE)
    health_text = font.render(f"HEALTH: {player_health}", True, WHITE)
    shield_text = font.render(f"SHIELD: {player_shield}", True, BLUE)
    wave_text = font.render(f"WAVE: {wave_number}", True, WHITE)
    current_time = pygame.time.get_ticks()
    weapon_status = "RELOADING" if (ammo[current_weapon] == 0 and current_time - reload_times[current_weapon] < 2000) else str(ammo[current_weapon])
    weapon_text = font.render(f"WEAPON: {current_weapon.upper()}", True, YELLOW)
    ammo_text = small_font.render(f"AMMO: {weapon_status}", True, YELLOW)
    window.blit(health_text, [10, 10])  # Left: Health
    window.blit(shield_text, [10, 50])  # Left: Shield below health
    window.blit(score_text, [width//2 - score_text.get_width()//2, 10])  # Middle: Score
    window.blit(wave_text, [playable_width - wave_text.get_width() - 10, 10])  # Right: Wave
    window.blit(weapon_text, [playable_width - weapon_text.get_width() - 10, 50])  # Right: Weapon below wave
    window.blit(ammo_text, [playable_width - ammo_text.get_width() - 10, 90])  # Right: Ammo below weapon
    pygame.draw.circle(window, RED, [int(crosshair_pos[0]), int(crosshair_pos[1])], 12, 2)
    pygame.draw.line(window, RED, [crosshair_pos[0] - 15, crosshair_pos[1]], [crosshair_pos[0] + 15, crosshair_pos[1]], 2)
    pygame.draw.line(window, RED, [crosshair_pos[0], crosshair_pos[1] - 15], [crosshair_pos[0], crosshair_pos[1] + 15], 2)
    pygame.draw.line(window, WHITE, [player_pos[0], player_pos[1]], [crosshair_pos[0], crosshair_pos[1]], 1)
    for explosion in explosions[:]:
        if explosion["radius"] < explosion["max_radius"]:
            explosion["radius"] += 6
        alpha = int(255 * (explosion["life"] / 20))
        surface = pygame.Surface((explosion["max_radius"]*2, explosion["max_radius"]*2), pygame.SRCALPHA)
        pygame.draw.circle(surface, (*ORANGE, alpha), (explosion["max_radius"], explosion["max_radius"]), int(explosion["radius"]))
        window.blit(surface, (int(explosion["pos"][0]) - explosion["max_radius"], int(explosion["pos"][1]) - explosion["max_radius"]))
        explosion["life"] -= 1
        if explosion["life"] <= 0:
            explosions.remove(explosion)
    for pickup in pickups:
        pickup.draw(window)
    for barricade in barricades:
        barricade.draw(window)

def reset_game():
    ammo = {"pistol": float('inf'), "smg": 50, "machine_gun": 60, "rocket": 2, "flamethrower": 100}
    pickups = [ShieldPickup() for _ in range(2)] + [AmmoPickup()] + [HealthKit()]
    barricades = [Barricade() for _ in range(3)]
    return [], [], 0, 100, 0, 1, [width//2, height//2], "playing", 180, 0, ammo, [], pygame.time.get_ticks(), {"pistol": 0, "smg": 0, "machine_gun": 0, "rocket": 0, "flamethrower": 0}, pickups, barricades, pygame.time.get_ticks()

def main():
    crosshair_pos = [width//2, height//2]  # Start in center of full screen
    zombies = []
    bullets = []
    score = 0
    high_score = 0
    player_health = 100
    player_shield = 0
    level = 1
    player_pos = [width//2, height//2]  # Start in center of full screen
    last_shoot_time = 0
    game_state = "menu"
    zombie_spawn_rate = 180
    pickup_spawn_rate = 1200
    current_weapon = "pistol"
    wave_number = 0
    ammo = {"pistol": float('inf'), "smg": 50, "machine_gun": 60, "rocket": 2, "flamethrower": 100}
    explosions = []
    last_switch_time = 0
    reload_times = {"pistol": 0, "smg": 0, "machine_gun": 0, "rocket": 0, "flamethrower": 0}
    pickups = [ShieldPickup() for _ in range(2)] + [AmmoPickup()] + [HealthKit()]
    barricades = [Barricade() for _ in range(3)]
    game_start_time = pygame.time.get_ticks()

    mixer.init()
    window = pygame.display.set_mode((width, height), pygame.FULLSCREEN | pygame.NOFRAME)
    pygame.display.set_caption("Zombie Outbreak")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 36)
    small_font = pygame.font.SysFont("consolas", 24)
    tiny_font = pygame.font.SysFont("consolas", 16)
    logging.info("Pygame initialized")

    shoot_sound = pygame.mixer.Sound(buffer=np.sin(2 * np.pi * np.arange(8000) * 440 / 44100).astype(np.float32))
    shoot_sound.set_volume(0.3)
    zombie_death_sound = pygame.mixer.Sound(buffer=np.sin(2 * np.pi * np.arange(8000) * 220 / 44100).astype(np.float32))
    zombie_death_sound.set_volume(0.4)
    game_over_sound = pygame.mixer.Sound(buffer=np.sin(2 * np.pi * np.arange(16000) * 110 / 44100).astype(np.float32))
    game_over_sound.set_volume(0.5)
    logging.info("Retro sounds generated")

    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise Exception("Failed to open webcam")
        logging.info("Webcam initialized")
    except Exception as e:
        logging.error(f"Webcam setup failed: {e}")
        pygame.quit()
        sys.exit()

    try:
        mp_hands = mp.solutions.hands
        hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.5, min_tracking_confidence=0.5)
        mp_draw = mp.solutions.drawing_utils
        logging.info("MediaPipe Hands initialized")
    except Exception as e:
        logging.error(f"Failed to initialize MediaPipe Hands: {e}")
        cap.release()
        pygame.quit()
        sys.exit()

    running = True
    zombie_spawn_timer = 0
    pickup_spawn_timer = 0
    max_zombies = 10
    boss_spawned = False

    while running:
        current_time = pygame.time.get_ticks()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    running = False
                elif event.key == pygame.K_SPACE:
                    if game_state in ["menu", "game_over"]:
                        high_score = max(high_score, score)
                        zombies, bullets, score, player_health, player_shield, level, player_pos, game_state, zombie_spawn_rate, wave_number, ammo, explosions, last_switch_time, reload_times, pickups, barricades, game_start_time = reset_game()

        for weapon in ammo:
            if ammo[weapon] == 0 and current_time - reload_times[weapon] >= 2000:
                ammo[weapon] = weapon_ammo_max[weapon]
                reload_times[weapon] = 0

        new_crosshair_pos, new_player_pos, shoot_triggered, new_weapon, camera_surface = get_hand_input(cap, hands, mp_hands, mp_draw, width, height, crosshair_pos, player_pos, current_weapon, last_switch_time, barricades)
        crosshair_pos = new_crosshair_pos
        player_pos = new_player_pos
        if new_weapon != current_weapon and current_time - last_switch_time > 5000:
            current_weapon = new_weapon
            last_switch_time = current_time
        if shoot_triggered and game_state == "playing":
            last_shoot_time, ammo = shoot(player_pos, crosshair_pos, current_weapon, bullets, shoot_sound, last_shoot_time, ammo, explosions)
            if ammo[current_weapon] == 0 and reload_times[current_weapon] == 0:
                reload_times[current_weapon] = current_time

        if game_state == "menu":
            draw_menu(window, font, small_font, tiny_font, high_score, camera_surface)
            pygame.display.update()
            clock.tick(60)
            continue

        if game_state == "game_over":
            draw_game_over(window, font, small_font, score, high_score, camera_surface)
            pygame.display.update()
            clock.tick(60)
            continue

        for bullet in bullets[:]:
            if bullet.update(barricades):
                if bullet.type == "rocket":
                    explosions.append({"pos": bullet.pos.copy(), "life": 20, "radius": 0, "max_radius": 100})
                bullets.remove(bullet)

        score = check_bullet_zombie_collisions(bullets, zombies, score, level, zombie_death_sound, explosions, barricades)
        player_health, player_shield, game_state = check_player_zombie_collisions(zombies, player_pos, player_health, player_shield, game_state, game_over_sound, zombie_death_sound, explosions)
        player_shield, player_health, ammo = check_player_pickup_collisions(pickups, player_pos, player_shield, player_health, ammo)

        if not zombies and game_state == "playing":
            wave_number += 1
            boss_spawned = False
            if wave_number % 3 == 0:
                zombie = Zombie("boss")
                zombie.health += level * 5
                zombies.append(zombie)
                boss_spawned = True
            else:
                for _ in range(max_zombies + wave_number):
                    zombie_type = random.choice(["normal", "fast", "strong", "exploding"])
                    zombies.append(Zombie(zombie_type))

        zombie_spawn_timer += 1
        if zombie_spawn_timer >= zombie_spawn_rate and len(zombies) < max_zombies + wave_number and not boss_spawned:
            zombie_type = random.choice(["normal", "fast", "strong", "exploding"])
            zombies.append(Zombie(zombie_type))
            zombie_spawn_timer = 0

        pickup_spawn_timer += 1
        if pickup_spawn_timer >= pickup_spawn_rate and len(pickups) < 6:
            pickup_type = random.choice([ShieldPickup, AmmoPickup, HealthKit])
            pickups.append(pickup_type())
            pickup_spawn_timer = 0

        for zombie in zombies:
            zombie.update(player_pos, level)

        draw_game_ui(window, font, small_font, tiny_font, score, player_health, player_shield, wave_number, current_weapon, crosshair_pos, player_pos, ammo, explosions, reload_times, pickups, barricades, camera_surface, game_start_time)
        draw_player(window, player_pos, game_start_time)
        for zombie in zombies:
            zombie.draw(window)
        for bullet in bullets:
            bullet.draw(window)

        pygame.display.update()
        clock.tick(60)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            running = False

    high_score = max(high_score, score)
    cap.release()
    cv2.destroyAllWindows()
    pygame.quit()

if __name__ == "__main__":
    main()