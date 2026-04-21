import pandas as pd
import hashlib
import json
import time

# ---------------- LOAD DATA ----------------
df = pd.read_csv("iov1_dataset.csv")

NUM_RSUS = 10
DIFFICULTY = 2

# ---------------- BLOCK CLASS ----------------
class Block:
    def __init__(self, index, vehicle_data, prev_hash, proposed_by):
        self.index = index
        self.timestamp = time.time()
        self.vehicle_data = vehicle_data

        self.prev_hash = prev_hash
        self.nonce = 0
        self.hash = None

        self.difficulty = DIFFICULTY
        self.mining_time = 0

        self.proposed_by = proposed_by
        self.mined_by = None
        self.validated_by = []

    def compute_hash(self):
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "vehicle_data": self.vehicle_data,
            "prev_hash": self.prev_hash,
            "nonce": self.nonce,
            "proposed_by": self.proposed_by
        }, sort_keys=True)

        return hashlib.sha256(block_string.encode()).hexdigest()

# ---------------- RSU NODE ----------------
class RSUNode:
    def __init__(self, rsu_id):
        self.rsu_id = rsu_id
        self.chain = []
        self.create_genesis_block()

    def create_genesis_block(self):
        genesis = Block(0, {"info": "Genesis"}, "0", self.rsu_id)
        genesis.hash = genesis.compute_hash()
        self.chain.append(genesis)

    def get_last_block(self):
        return self.chain[-1]

    def add_block(self, block):
        self.chain.append(block)

# ---------------- INIT RSUs ----------------
rsus = [RSUNode(i) for i in range(NUM_RSUS)]

# ---------------- MINING (PROPOSER ONLY) ----------------
def mine_block(block):

    prefix = "0" * DIFFICULTY
    start_time = time.time()

    while True:
        block.nonce += 1
        hash_val = block.compute_hash()

        if hash_val.startswith(prefix):
            block.hash = hash_val
            block.mined_by = block.proposed_by
            block.mining_time = time.time() - start_time
            return block

# ---------------- POST VALIDATION ----------------
def post_validate(block):
    if not block.hash.startswith("0" * block.difficulty):
        return False

    block.validated_by = [
       rsu.rsu_id for rsu in rsus 
       if rsu.rsu_id != block.mined_by]
    return True

# ---------------- MAIN PROCESS ----------------
for _, row in df.iterrows():

    data = row.to_dict()

    vehicle_data = {
        "vehicle_id": data["vehicle_id"],
        "rsu_id": data["rsu_id"],
        "distance": data["distance"],
        "speed": data["speed"],
        "accel": data["accel"],
        "neighbors": data["neighbors"],
        "msgRate": data["msgRate"],
        "delay": data["delay"],
        "drop": data["drop"],
        "fmr": data["fmr"],
        "trust": data["trust"],
        "behavior": data["behavior"],
        "attack": data["attack"]
    }

    # 👉 PROPOSER = MINER
    proposer = rsus[int(data["rsu_id"])]

    new_block = Block(
        index=proposer.get_last_block().index + 1,
        vehicle_data=vehicle_data,
        prev_hash=proposer.get_last_block().hash,
        proposed_by=proposer.rsu_id
    )

    # ⛏️ MINING (ONLY PROPOSER)
    mined_block = mine_block(new_block)

    # ✅ VALIDATION
    if not post_validate(mined_block):
        continue

    # 📡 BROADCAST
    for rsu in rsus:
        rsu.add_block(mined_block)

# ---------------- SAVE BLOCKCHAIN ----------------
chain_data = [block.__dict__ for block in rsus[0].chain]
pd.DataFrame(chain_data).to_csv("blockchain1_log.csv", index=False)

# ---------------- FINAL OUTPUT ----------------
print("\n🔗 Final Blockchain Length:", len(rsus[0].chain))
print("✅ Blockchain Logging Completed")