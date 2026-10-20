
from fastapi import FastAPI
from transaction import Transaction
import time
import asyncio
import httpx
from pydantic import BaseModel
from peer import Peer

app = FastAPI()


# @app.get("/")
# def read_root():
#     return {"Hello": "World"}


# @app.get("/items/{item_id}")
# def read_item(item_id: int, q: Union[str, None] = None):
#     return {"item_id": item_id, "q": q}


# !================================== work starts here ========================================
# main.py
from node import Node
import uvicorn

app = FastAPI(title="Coinbase Node")

# Create the bootstrap node (genesis = True) and gieve it initial money 
coinbase = Node(name="coinbase",port=5000, difficulty=3, is_genesis=True)

# Moved initial mining to functionality that runs via asyncio
async def perform_initial_mining():
    print("[coinbase] Mining 3 initial blocks for starter funds...")
    for i in range(3):
        await coinbase.mine_block()
        await asyncio.sleep(0.5)
    print(f"[coinbase] Ready — has {coinbase.get_balance()} coins")








# ?? ===========  here is the new  ====================
# ---------- PEER REGISTRY ----------
# UPDATED: Store Peer objects instead of simple dict
peer_registry = {}  # {uuid: Peer}

class PeerRegistration(BaseModel):
    name: str
    port: int
    uuid: str
    host: str = "127.0.0.1"



@app.post("/register")
async def register_node(registration: PeerRegistration):
    """New node registers with coinbase"""
    peer = Peer(
        name=registration.name,
        port=registration.port,
        host=registration.host,
        peer_uuid=registration.uuid
    )
    
    # Add to registry
    peer_registry[peer.uuid] = peer
    
    # Add to coinbase's peer list
    coinbase.add_peer(peer)
    
    print(f"[coinbase] Registered new peer: {peer.name} ({peer.uuid})")
    
    # Notify all existing peers about the new peer
    await notify_peers_about_new_node(peer)

    # Return list of all OTHER peers (exclude the registering node)
    other_peers = [
        p.to_dict() 
        for p in peer_registry.values() 
        if p.uuid != peer.uuid
    ]
    
    return {
        "status": "registered",
        "your_uuid": peer.uuid,
        "coinbase_uuid": coinbase.uuid, 
        "peers": other_peers
    }



async def notify_peers_about_new_node(new_peer: Peer):
    """Notify all existing peers about a new node joining"""
    print(f"[coinbase] Notifying existing peers about {new_peer.name}...")
    
    async with httpx.AsyncClient() as client:
        for peer in peer_registry.values():
            if peer.uuid == new_peer.uuid:  # Don't notify the new peer about itself
                continue
                
            try:
                response = await client.post(
                    f"{peer.url}/new_peer",
                    json=new_peer.to_dict(),
                    timeout=2.0
                )
                if response.status_code == 200:
                    print(f"[coinbase] ✓ Notified {peer.name} about {new_peer.name}")
            except Exception as e:
                print(f"[coinbase] ✗ Failed to notify {peer.name}: {e}")


@app.get("/peers")
def get_all_peers():
    """Get list of all registered peers"""
    return {
        "count": len(peer_registry),
        "peers": [p.to_dict() for p in peer_registry.values()]
    }



# Expose the node globally so we can add routes
@app.get("/chain")
def get_chain():
    """Return the blockchain"""
    a = [block.__dict__ for block in coinbase.blockchain.chain]
    # print(a)
    return a





# -----------------------------------------------------


class FaucetRequest(BaseModel):
    node_name: str


@app.post("/faucet")
async def faucet_request(request: FaucetRequest):
    """New node asks for initial money"""
    node_name = request.node_name
    print(f"[coinbase] Faucet request from {node_name}")
    
    tx = Transaction(sender="COINBASE", receivers={node_name: 100}, amount=100)
    tx.timestamp = time.time()
    
    # Add to coinbase's mempool and broadcast
    coinbase.pending_transactions.append(tx)
    await coinbase.broadcast_transaction(tx)
    
    return {"status": "100 coins sent", "to": node_name}



@app.get("/balance/{node_name}")
def get_balance(node_name: str):
    """Get balance for any node"""
    from wallet import calculate_balance
    balance = calculate_balance(coinbase.blockchain, node_name)
    return {"node": node_name, "balance": balance}



# ======= now the block reception =========== #! there will be a lot of work on this later

@app.post("/validate_block")
async def validate_block_endpoint(block_data: dict):
    """(Phase 1) Receive a validation request"""
    from block import Block
    
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
    
    vote = "YES" if coinbase.handle_validation_request(block) else "NO"
    return {"status": "voted", "vote": vote}

@app.post("/commit_block")
async def commit_block_endpoint(block_data: dict):
    """(Phase 2) Receive a commit command for a winner block"""
    from block import Block
    
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
    
    coinbase.handle_commit_request(block)
    return {"status": "committed"}


@app.post("/receive_transaction")
def receive_transaction_endpoint(tx_data: dict):
    """Receive a transaction from another node"""
    tx = Transaction(tx_data['sender'], tx_data['receivers'], tx_data['amount'])
    tx.timestamp = tx_data['timestamp']
    
    coinbase.receive_transaction(tx)
    return {"status": "received"}

# -----------------------------------------------------------------------------------------------------
# now for rest clients : endpoints
@app.post("/transaction/create")
async def create_transaction(receivers: dict, amount: float):
    """Create and broadcast a transaction"""
    try:
        balance = coinbase.get_balance()
        if balance < amount:
            return {
                "status": "error",
                "message": f"Insufficient funds. Balance: {balance}, Required: {amount}"
            }
        
        await coinbase.create_and_broadcast_transaction(receivers, amount)
        return {
            "status": "success",
            "message": f"Transaction created: coinbase → {receivers} ({amount} coins)",
            "from": "coinbase",
            "receivers": receivers,
            "amount": amount
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/mine")
async def trigger_mining():
    """Trigger mining of a new block"""
    try:
        if coinbase.is_mining:
            return {"status": "error", "message": "Already mining"}
        
        block = await coinbase.mine_block()
        
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
def get_coinbase_status():
    """Get coinbase node status"""
    try:
        balance = coinbase.get_balance()
        
        peers_info = []
        for peer in coinbase.peers.values():
            peers_info.append({
                "name": peer.name,
                "url": peer.url,
                "alive": peer.is_alive
            })
        
        return {
            "node": "coinbase",
            "uuid": coinbase.uuid,
            "url": "http://127.0.0.1:5000",
            "balance": balance,
            "blockchain_length": len(coinbase.blockchain.chain),
            "pending_transactions": len(coinbase.pending_transactions),
            "peers_count": len(coinbase.peers),
            "peers": peers_info,
            "is_mining": coinbase.is_mining
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/mempool")
def get_coinbase_mempool():
    """Get pending transactions"""
    try:
        return {
            "count": len(coinbase.pending_transactions),
            "transactions": [tx.__dict__ for tx in coinbase.pending_transactions]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# -----------------------------------------------------------------------------------------------

# REPL so you can type commands while server runs
def repl():
    print(f"[base] Interactive mode ready! Type commands below:-----------")
    print("node.create_and_broadcast_transaction({'Bob': 10}, 10)")
    print("node.mine_block()")
    print("node.display_status()")
    print("-"*20)
    while True:
        try:
            cmd = input(f"[base]> ")
            if cmd.strip():
                exec(cmd)
        except Exception as e:
            print(f"Error: {e}")



import threading

if __name__ == "__main__":
    print("\n" + "="*60)
    print("Starting Coinbase node (bootstrap) on http://127.0.0.1:5000")
    print(f"Coinbase UUID: {coinbase.uuid}")
    print("="*60 + "\n")
    
    # Run initial mining
    asyncio.run(perform_initial_mining())
    
    uvicorn.run(app, host="127.0.0.1", port=5000)

    # todo : fix it later to work with this 
    # threading.Thread(target=uvicorn.run, args=("__main__:app",), 
    #                 kwargs={"host": "127.0.0.1", "port": 5000}, 
    #                 daemon=True).start()
    




