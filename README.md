# Zombie Outbreak – Hand Tracking Game

A **retro-inspired zombie survival game** powered by **Pygame**, **OpenCV**, and **MediaPipe Hands**.
Control your player using **hand tracking gestures** captured through your webcam — move, aim, switch weapons, and shoot zombies without touching the keyboard or mouse.

---

## 🎮 Features

* **Hand Tracking Controls**

  * Move player with wrist movement
  * Aim with index finger
  * Pinch (thumb + index) to shoot
  * Switch weapons using finger counts

    * ✌️ 2 fingers → SMG
    * 🤟 3 fingers → Machine Gun
    * ✋ 4 fingers → Rocket

* **Weapons**

  * Pistol (infinite ammo)
  * SMG, Machine Gun, Rocket Launcher, Flamethrower (limited ammo + reload system)

* **Zombies**

  * Normal, Fast, Strong, Exploding, and Boss types
  * Scaling difficulty with waves

* **Pickups**

  * Health Kits
  * Shield Boosts
  * Ammo Refills

* **Environment**

  * Destructible barricades
  * Explosions and retro sound effects

---

## 🖥 Requirements

Make sure you have **Python 3.8+** installed.
Install dependencies with:

```bash
pip install pygame opencv-python mediapipe numpy
```

---

## ▶️ How to Run

1. Clone/download this repository.
2. Connect a **webcam**.
3. Run the game:

```bash
python Zombie_handtracking_game.py
```

4. Play in **fullscreen mode** — press **Q** anytime to quit.

---

## 🎯 Gameplay Instructions

* Survive waves of zombies as long as possible.
* Collect pickups to restore health, shield, and ammo.
* Use hand gestures to control movement and weapons.
* High score is tracked between runs.

---

## ⌨️ Keyboard Shortcuts

* **SPACE** → Start / Restart game
* **Q** → Quit game

---

## 📸 Notes

* The game uses **your webcam** for gesture recognition.
* Ensure good lighting and keep your hand visible to improve tracking accuracy.
* MediaPipe supports **one hand at a time** in this version.


## 📜 License

This project is open-source for learning and personal use.

---
