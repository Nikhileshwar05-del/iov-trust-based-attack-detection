import traci
import pandas as pd
import math
import random
from collections import deque

random.seed(42)

SUMO_CMD = ["sumo-gui", "-c", "osm.sumocfg", "--seed", "42"]
WINDOW = 10
RSU_RANGE = 500

RSUs = [
    (1961.87, 1248.47),
    (1836.28, 1371.98),
    (1743.19, 1520.12),
    (2037.46, 1638.67),
    (2323.44, 1417.15),
    (2556.66, 1518.21),
    (2351.64, 1121.28),
    (1572.97, 1335.97),
    (1958.76, 1692.27),
    (3027.93, 1654.31)
]

traci.start(SUMO_CMD)

# RSU markers
for i, (x, y) in enumerate(RSUs):
    traci.poi.add(f"RSU_{i}", x, y, (255, 0, 0, 255), 25, 25)

traci.gui.setZoom("View #0", 3000)

data = []
fmr_window = {}
vehicle_round = {}

ATTACK_TYPES = ["DoS", "Sybil", "Spoofing", "FalseData"]
attack_index = 0

# ---------------- UTIL ----------------
def add_noise(value, percent=0.1):
    return value + value * percent * random.uniform(-1, 1)

def get_neighbors(vehicle_id, radius=100):
    x1, y1 = traci.vehicle.getPosition(vehicle_id)
    count = 0
    for v in traci.vehicle.getIDList():
        if v == vehicle_id:
            continue
        x2, y2 = traci.vehicle.getPosition(v)
        if math.hypot(x1-x2, y1-y2) < radius:
            count += 1
    return count

def get_dynamic_weights(msgRate, delay, fmr, drop, neighbors):
    w_fmr, w_drop, w_msg, w_delay = 0.3, 0.25, 0.2, 0.2

    if fmr > 0.4: w_fmr += 0.3
    if drop > 0.5: w_drop += 0.3
    if msgRate > 6: w_msg += 0.2
    if delay > 0.05: w_delay += 0.2
    if neighbors > 20:
        w_msg += 0.2
        w_drop += 0.2

    total = w_fmr + w_drop + w_msg + w_delay
    return w_fmr/total, w_drop/total, w_msg/total, w_delay/total

# ---------------- SIMULATION ----------------
try:
    while True:
        traci.simulationStep()

        if traci.simulation.getMinExpectedNumber() <= 0:
            break

        for vid in traci.vehicle.getIDList():

            speed = traci.vehicle.getSpeed(vid) * 3.6
            accel = traci.vehicle.getAcceleration(vid)
            x, y = traci.vehicle.getPosition(vid)

            neighbors = get_neighbors(vid)

            for rsu_id, (rx, ry) in enumerate(RSUs):

                distance = math.hypot(x - rx, y - ry)
                if distance > RSU_RANGE:
                    continue

                # 🔥 ROUND PER VEHICLE
                if vid not in vehicle_round:
                    vehicle_round[vid] = 0
                vehicle_round[vid] += 1
                round_no = vehicle_round[vid]

                # -------- FEATURES --------
                msgRate = add_noise((speed / 12) + (neighbors / 6))
                delay = add_noise(distance / 3e8 + neighbors * 0.002)

                drop = min(1, (distance / 2000) + (neighbors / 50))
                drop = max(0, min(add_noise(drop), 1))

                # -------- FMR --------
                if vid not in fmr_window:
                    fmr_window[vid] = deque(maxlen=WINDOW)

                base_fmr = 0.05
                if abs(accel) > 6:
                    base_fmr += 0.3
                base_fmr += min(speed / 200, 0.2)

                fmr_window[vid].append(base_fmr)
                fmr = sum(fmr_window[vid]) / len(fmr_window[vid])
                fmr = max(0, min(add_noise(fmr), 1))

                # -------- NORMALIZATION --------
                norm_msg = min(msgRate / 10, 1)
                norm_delay = min(delay / 0.1, 1)

                # -------- TRUST --------
                w_fmr, w_drop, w_msg, w_delay = get_dynamic_weights(
                    msgRate, delay, fmr, drop, neighbors
                )

                trust = 1 - (
                    w_fmr*fmr +
                    w_drop*drop +
                    w_msg*norm_msg +
                    w_delay*norm_delay
                )

                trust = max(0, min(add_noise(trust, 0.05), 1))

                # -------- BEHAVIOR --------
                if trust > 0.75:
                    behavior = "Normal"
                elif trust > 0.6:
                    behavior = "Suspicious"
                elif trust > 0.45:
                    behavior = "Critical"
                else:
                    behavior = "Malicious"

                # -------- ATTACK --------
                attack = "None"

                if behavior in ["Critical", "Malicious"]:

                    if random.random() < 0.5:

                        attack = ATTACK_TYPES[attack_index % len(ATTACK_TYPES)]

                        if random.random() < 0.35:
                            attack_index += 1

                        # modify features (keep your logic)
                        if attack == "DoS":
                            msgRate *= random.uniform(2, 3.5)
                            drop = min(1, drop + 0.3)

                        elif attack == "Sybil":
                            neighbors += random.randint(10, 25)

                        elif attack == "Spoofing":
                            delay *= random.uniform(1.5, 3)

                        elif attack == "FalseData":
                            speed = random.choice([0, speed * 1.5, -abs(speed)])
                            accel = random.uniform(-8, 8)
                            fmr = min(1, fmr + 0.4)

                # -------- STORE (REAL ATTACK EFFECTS) --------
                rows = []

                if attack == "DoS":
                    for _ in range(random.randint(3, 6)):
                        vehicle_round[vid] += 1
                        rows.append([
                            vehicle_round[vid], vid, rsu_id, distance,
                            speed, accel, neighbors,
                            msgRate, delay, drop, fmr,
                            trust, behavior, "DoS"
                        ])

                elif attack == "Sybil":
                    for i in range(random.randint(2, 5)):
                        vehicle_round[vid] += 1
                        fake_id = f"{vid}_S{i}"
                        rows.append([
                            vehicle_round[vid], fake_id, rsu_id, distance,
                            speed, accel, neighbors,
                            msgRate, delay, drop, fmr,
                            trust, behavior, "Sybil"
                        ])

                elif attack == "Spoofing":
                    vehicle_round[vid] += 1
                    victim = random.choice(traci.vehicle.getIDList())
                    rows.append([
                        vehicle_round[vid], victim, rsu_id, distance,
                        speed, accel, neighbors,
                        msgRate, delay, drop, fmr,
                        trust, behavior, "Spoofing"
                    ])

                elif attack == "FalseData":
                    vehicle_round[vid] += 1
                    rows.append([
                        vehicle_round[vid], vid, rsu_id, distance,
                        speed, accel, neighbors,
                        msgRate, delay, drop, fmr,
                        trust, behavior, "FalseData"
                    ])

                else:
                    rows.append([
                        round_no, vid, rsu_id, distance,
                        speed, accel, neighbors,
                        msgRate, delay, drop, fmr,
                        trust, behavior, "None"
                    ])

                for r in rows:
                    data.append(r)

except Exception as e:
    print("Error:", e)

# -------- SAVE --------
df = pd.DataFrame(data, columns=[
    "round","vehicle_id","rsu_id","distance",
    "speed","accel","neighbors",
    "msgRate","delay","drop","fmr",
    "trust","behavior","attack"
])

df.to_csv("iov1_dataset.csv", index=False)

traci.close()
print("✅ FINAL REALISTIC ATTACK CODE READY")