# other_node.py
from node import Node
from fastapi import FastAPI
import uvicorn
import requests
import time


import uvicorn
import httpx
import threading
import time
import asyncio
from block import Block
from transaction import Transaction
import sys  
from peer import Peer


from fastapi import FastAPI


COINBASE_URL = "http://127.0.0.1:5000"


app = FastAPI()


#replaces the hardcoded NAME and PORT
if len(sys.argv) < 3:
    print("Usage: python other_node.py <NAME> <PORT>")
    print("Example: python other_node.py Alice 8001")
    sys.exit(1)


NAME = sys.argv[1]      # Get from command line
PORT = int(sys.argv[2]) # ← change (8001, 8002, 8003, 8004...)





node = Node(name=NAME, port=PORT,difficulty=3, is_genesis=False)
peer_nodes = [] 
node_loop = None # Global to store the event loop for REPL interaction

async def set_global_loop():
    global node_loop
    node_loop = asyncio.get_running_loop() 



async def sync_from_coinbase():
    print(f"[{NAME}] Waiting for coinbase node...")
    async with httpx.AsyncClient() as client:
        while True:
            try:
                r = await client.get(f"{COINBASE_URL}/chain", timeout=5.0)
                if r.status_code == 200:
                    chain = r.json()

                    node.blockchain.chain = []
                    # Imports already at top
                    for b in chain:
                        txs = [Transaction(t['sender'], t['receivers'], t['amount']) for t in b['transactions']]
                        block = Block(b['index'], txs, b['previous_hash'])
                        block.nonce = b['nonce']
                        block.hash = b['hash']
                        block.merkle_root = b['merkle_root']
                        block.timestamp = b['timestamp']
                        node.blockchain.chain.append(block)
                    print(f"[{NAME}] Synced {len(chain)} blocks from coinbase")
                    break
            except Exception as e:
                # print(e)
                pass
            await asyncio.sleep(2)


# Auto-sync on startup
threading.Thread(target=sync_from_coinbase, daemon=True).start()



async def register_with_coinbase():
    """Register with coinbase and discover peers"""
    await asyncio.sleep(3)  # Wait for own server to start
    
    try:
        # Send registration with our info
        registration_data = {
            "name": NAME,
            "port": PORT,
            "uuid": str(node.uuid),
            "host": "127.0.0.1"
        }

        async with httpx.AsyncClient() as client:
            r = await client.post(f"{COINBASE_URL}/register", json=registration_data)
            
            if r.status_code == 200:
                response = r.json()
                print(f"[{NAME}] ✓ Registered with coinbase!")
                print(f"[{NAME}] My UUID: {node.uuid[:8]}...")
                
    
                # Add coinbase as peer
                coinbase_uuid = response.get("coinbase_uuid")  
                if coinbase_uuid:
                    coinbase_peer = Peer("coinbase", 5000, peer_uuid=coinbase_uuid)
                    node.add_peer(coinbase_peer)
    
                # Add all other peers
                peers_list = response.get("peers", [])
                print(f"[{NAME}] Discovered {len(peers_list)} other peers")
                
                for peer_data in peers_list:
                    peer = Peer.from_dict(peer_data)
                    node.add_peer(peer)
                    print(f"[{NAME}]   - {peer.name} at {peer.url}")
                
    except Exception as e:
        print(f"[{NAME}] Registration failed: {e}")





async def periodic_peer_sync():
    """Periodically sync peer list from coinbase"""
    async with httpx.AsyncClient() as client:
        while True:
            await asyncio.sleep(30)  # Every 30 seconds
            try:
                r = await client.get(f"{COINBASE_URL}/peers", timeout=2.0)
                if r.status_code == 200:
                    data = r.json()
                    for peer_data in data.get("peers", []):
                        peer = Peer.from_dict(peer_data)
                        if peer.uuid != node.uuid and peer.uuid not in node.peers:
                            node.add_peer(peer)
                            print(f"[{NAME}] 🔔 Discovered new peer: {peer.name}")
            except:
                pass




async def request_funds():
    """Request initial funds from faucet"""
    await asyncio.sleep(5)  # Wait for registration to complete
    
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{COINBASE_URL}/faucet", json={"node_name": NAME})
            if r.status_code == 200:
                print(f"[{NAME}] ✓ Faucet success! 100 coins received")
                
                # Mine the block
                await asyncio.sleep(2)
                print(f"[{NAME}] Mining the faucet transaction...")
                await node.mine_block()
    except Exception as e:
        print(f"[{NAME}] Faucet failed: {e}")

def repl():
    """Interactive REPL for commands in main thread"""
    print("-"*40)
    print(f"\n[{NAME}] Interactive mode ready! Type commands below:")
    print("Examples:")
    print("  node.create_and_broadcast_transaction({'other_node's_name': 10}, 10)")
    print("  node.mine_block()")
    print("  node.display_status()")
    print("  node.get_balance()")
    print("NOTE: Async methods will be scheduled on the background event loop.")
    print("-" * 40,"\n")
    
    while True:
        try:
            cmd = input(f"{NAME}> ")
            if cmd.strip():
                # Hacky support for top-level await in REPL
                # Since we can't easily await, we wrap calls to schedule them
                if "node." in cmd and "display" not in cmd and "get_balance" not in cmd:
                   # For async commands, schedule them
                   # This assumes simple calls. User logic: exec(cmd)
                   # We need to wrap exec to handle async return
                   
                   # Construct a wrapper to run the cmd
                   # Logic: execute cmd. If result is coroutine, schedule it.
                   wrapped_cmd = f"""
import asyncio
res = {cmd}
if asyncio.iscoroutine(res):
    if node_loop:
        future = asyncio.run_coroutine_threadsafe(res, node_loop)
        try:
            print("Result:", future.result(timeout=10))
        except Exception as e:
            print("Async execution error:", e)
else:
    print(res)
"""
                   exec(wrapped_cmd)
                else:
                    exec(cmd)
        except Exception as e:
            print(f"Error: {e}")







# ---------- FASTAPI ENDPOINTS ----------
@app.get("/")
def home():
    return {
        "node": NAME,
        "uuid": node.uuid,
        "blocks": len(node.blockchain.chain),
        "peers": len(node.peers),
        "balance": node.get_balance()
    }

@app.get("/info")
def get_info():
    """Return node information"""
    return node.get_peer_info()

@app.post("/validate_block")
async def validate_block_endpoint(block_data: dict):
    """(Phase 1) Receive a validation request"""
    # helper to restore tx
    def restore_tx(data):
        t = Transaction(data['sender'], data['receivers'], data['amount'])
        t.timestamp = data['timestamp']
        return t

    txs = [restore_tx(t) for t in block_data['transactions']]
    block = Block(block_data['index'], txs, block_data['previous_hash'])
    block.nonce = block_data['nonce']
    block.hash = block_data['hash']
    block.merkle_root = block_data['merkle_root']
    block.timestamp = block_data['timestamp']
    
    vote = "YES" if node.handle_validation_request(block) else "NO"
    return {"status": "voted", "vote": vote}

@app.post("/commit_block")
async def commit_block_endpoint(block_data: dict):
    """(Phase 2) Receive a commit command for a winner block"""
    # helper to restore tx
    def restore_tx(data):
        t = Transaction(data['sender'], data['receivers'], data['amount'])
        t.timestamp = data['timestamp']
        return t

    txs = [restore_tx(t) for t in block_data['transactions']]
    block = Block(block_data['index'], txs, block_data['previous_hash'])
    block.nonce = block_data['nonce']
    block.hash = block_data['hash']
    block.merkle_root = block_data['merkle_root']
    block.timestamp = block_data['timestamp']
    
    node.handle_commit_request(block)
    return {"status": "committed"}

@app.post("/receive_transaction")
def receive_transaction_endpoint(tx_data: dict):
    """Receive a transaction from another node"""
    tx = Transaction(tx_data['sender'], tx_data['receivers'], tx_data['amount'])
    tx.timestamp = tx_data['timestamp']
    
    node.receive_transaction(tx)
    return {"status": "received"}

@app.post("/new_peer")
def new_peer_notification(peer_data: dict):
    """Receive notification about a new peer joining the network"""
    peer = Peer.from_dict(peer_data)
    added = node.add_peer(peer)
    if added:
        print(f"\n[{NAME}] 🔔 New peer joined: {peer.name} at {peer.url}")
    return {"status": "acknowledged"}


# ! ================= now the cmd funcs as endpoints ==================
# ---------- COMMAND ENDPOINTS ----------
@app.post("/transaction/create")
async def create_transaction(receivers: dict, amount: float):
    """Create and broadcast a transaction"""
    try:
        # Check balance first
        balance = node.get_balance()
        if balance < amount:
            return {
                "status": "error",
                "message": f"Insufficient funds. Balance: {balance}, Required: {amount}"
            }
        
        await node.create_and_broadcast_transaction(receivers, amount)
        return {
            "status": "success",
            "message": f"Transaction created: {NAME} → {receivers} ({amount} coins)",
            "from": NAME,
            "receivers": receivers,
            "amount": amount
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/mine")
async def trigger_mining():
    """Trigger mining of a new block"""
    try:
        if node.is_mining:
            return {"status": "error", "message": "Already mining"}
        
        pending_count = len(node.pending_transactions)
        block = await node.mine_block()
        
        if block:
            return {
                "status": "success",
                "message": f"Block #{block.index} mined successfully!",
                "block_index": block.index,
                "transactions_included": len(block.transactions),
                "reward": 50,
                "hash": block.hash
            }
        else:
            return {"status": "error", "message": "Mining failed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/status")
def get_status():
    """Get node status (like display_status but returns JSON)"""
    try:
        balance = node.get_balance()
        
        peers_info = []
        for peer in node.peers.values():
            peers_info.append({
                "name": peer.name,
                "url": peer.url,
                "alive": peer.is_alive
            })
        
        return {
            "node": NAME,
            "uuid": node.uuid,
            "url": node.url,
            "balance": balance,
            "blockchain_length": len(node.blockchain.chain),
            "pending_transactions": len(node.pending_transactions),
            "peers_count": len(node.peers),
            "peers": peers_info,
            "is_mining": node.is_mining
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/balance")
def get_balance_endpoint():
    """Get node balance"""
    try:
        balance = node.get_balance()
        return {
            "node": NAME,
            "balance": balance
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/chain")
def get_chain():
    """Get the full blockchain"""
    try:
        chain_data = []
        for block in node.blockchain.chain:
            chain_data.append({
                "index": block.index,
                "timestamp": block.timestamp,
                "transactions": [tx.__dict__ for tx in block.transactions],
                "previous_hash": block.previous_hash,
                "hash": block.hash,
                "nonce": block.nonce,
                "merkle_root": block.merkle_root
            })
        return {
            "length": len(chain_data),
            "chain": chain_data
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/mempool")
def get_mempool():
    """Get pending transactions"""
    try:
        return {
            "count": len(node.pending_transactions),
            "transactions": [tx.__dict__ for tx in node.pending_transactions]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ---------- STARTUP ----------
# ---------- STARTUP ----------

@app.on_event("startup")
async def startup_event():
    """Start background tasks when app starts"""
    await set_global_loop()
    asyncio.create_task(sync_from_coinbase())
    asyncio.create_task(register_with_coinbase())
    asyncio.create_task(periodic_peer_sync())
    asyncio.create_task(request_funds())


if __name__ == "__main__":
    # Start FastAPI in background thread to allow REPL in main thread
    # NOTE: This setup allows the REPL to work while Uvicorn runs
    # Uvicorn will have its own event loop in its thread.
    threading.Thread(
        target=uvicorn.run, 
        args=("__main__:app",), 
        kwargs={"host": "127.0.0.1", "port": PORT, "log_level": "info"}, 
        daemon=True
    ).start()
    
    print(f"Node {NAME} running on http://127.0.0.1:{PORT}")

    # Start REPL (main thread)
    repl()