# node.py
from blockchain import Blockchain
from transaction import Transaction
from wallet import calculate_balance
import time
import httpx
import asyncio
import uuid
from peer import Peer

class Node:
    """
    Represents a blockchain node in a P2P network
    Each node has its own blockchain copy and can communicate with other nodes
    """

    
    def __init__(self, name,port ,difficulty=3 ,is_genesis=False):
        self.name = name
        self.uuid = str(uuid.uuid4())
        # print("uuid----- =",self.uuid)
        self.blockchain = Blockchain(difficulty=difficulty ,genesis=is_genesis)
        
        # self.peers = []  
        # self.peer_urls = []  
        self.peers = {}
        
        self.pending_transactions = []  # Mempool
        self.is_mining = False
        
        # New Consensus State
        self.suggested_block = None  # Holds the current block being voted on
        self.votes_received = 0
        self.vote_threshold = 0.5    # Simple majority > 50%
        self.mining_event = None     # For synchronizing validation wait

        self.port = port

        self.host = "127.0.0.1"
        self.url = f"http://{self.host}:{self.port}"

        print(f"[{self.name}] Node initialized" + (" genesis (BOOTSTRAP)" if is_genesis else ""))
        print(f"[{self.name}] UUID: {self.uuid}")
        print(f"[{self.name}] URL: {self.url}")



    #! --------------- now peer-related methods 
    def connect_to_peer(self, peer_node):
        """Add another node as a peer (local simulation helper)"""
        # Adapted to work with the dict structure if peer_node is a Node object
        if peer_node.uuid not in self.peers and peer_node != self:
             # Create a proxy Peer object from the Node object
            from peer import Peer
            p = Peer(peer_node.name, peer_node.port, peer_node.host, peer_node.uuid)
            self.peers[p.uuid] = p
            print(f"[{self.name}] Connected to {peer_node.name}")
    
    def add_peer(self, peer: Peer):
        """Add a peer to the network"""
        if peer.uuid != self.uuid and peer.uuid not in self.peers:
            self.peers[peer.uuid] = peer
            print(f"[{self.name}] Added peer: {peer.name} ({peer.uuid[:8]}...) at {peer.url}")
            return True
        return False
    
    def remove_peer(self, peer_uuid: str):
        """Remove a peer from the network"""
        if peer_uuid in self.peers:
            removed = self.peers.pop(peer_uuid)
            print(f"[{self.name}] Removed peer: {removed.name}")
            return True
        return False
    
    def get_peer_by_name(self, name: str) -> Peer:
        """Find peer by name"""
        for peer in self.peers.values():
            if peer.name == name:
                return peer
        return None
    
    def get_all_peer_urls(self) -> list:
        """Get list of all peer URLs"""
        return [peer.url for peer in self.peers.values() if peer.is_alive]

    def get_peer_info(self) -> dict:
        """Return this node's info as a Peer dict"""
        return {
            "name": self.name,
            "uuid": self.uuid,
            "host": self.host,
            "port": self.port,
            "url": self.url
        }
    


    # -----------------

    async def broadcast_transaction(self, transaction):
        """
        Send transaction to all peers via HTTP (Async)
        """
        print(f"\n[{self.name}] Broadcasting transaction: {transaction}")
        
        # Add to own mempool
        self.pending_transactions.append(transaction)
        
        # Prepare transaction data for JSON
        tx_data = {
            'sender': transaction.sender,
            'receivers': transaction.receivers,
            'amount': transaction.amount,
            'timestamp': transaction.timestamp
        }
        
        # Send to all peers via HTTP
        async with httpx.AsyncClient() as client:
            for peer in self.peers.values():
                if not peer.is_alive:
                    continue
                
                try:
                    response = await client.post(
                        f"{peer.url}/receive_transaction",
                        json=tx_data,
                        timeout=2.0
                    )
                    if response.status_code == 200:
                        print(f"[{self.name}] ✓ Sent transaction to {peer.name}")
                    else:
                        print(f"[{self.name}] ✗ Failed to send transaction to {peer.name}")
                except Exception as e:
                    print(f"[{self.name}] ✗ Error sending transaction to {peer.name}: {e}")
                    peer.is_alive = False



    def receive_transaction(self, transaction):
        """Receive transaction from another node"""
        print(f"[{self.name}] Received transaction from network")
        
        # Verify transaction (check amount >0 and sender has balance)
        if transaction.amount <= 0:
            print(f"[{self.name}] Invalid transaction rejected (amount <=0)")
            return
        
        # Check sender balance (skip for COINBASE tx)
        if transaction.sender != "COINBASE":
            sender_balance = calculate_balance(self.blockchain, transaction.sender)
            if sender_balance < transaction.amount:
                print(f"[{self.name}] Invalid transaction rejected (insufficient funds for {transaction.sender})")
                return
            
        
        #  Check if transaction already exists in blockchain
        for block in self.blockchain.chain:
            for tx in block.transactions:
                if (tx.sender == transaction.sender and 
                    tx.receivers == transaction.receivers and 
                    tx.amount == transaction.amount and
                    abs(tx.timestamp - transaction.timestamp) < 60):  # Within 1 minute
                    print(f"[{self.name}] Transaction already in blockchain, skipping")
                    return
        
        # Check if already in mempool
        for tx in self.pending_transactions:
            if (tx.sender == transaction.sender and 
                tx.receivers == transaction.receivers and 
                tx.amount == transaction.amount and
                abs(tx.timestamp - transaction.timestamp) < 60):
                print(f"[{self.name}] Transaction already in mempool, skipping")
                return
        
        self.pending_transactions.append(transaction)
        print(f"[{self.name}] Transaction added to mempool")





    async def create_and_broadcast_transaction(self, receivers, amount):
        """Create a new transaction and broadcast it"""
        # Check own balance first
        my_balance = self.get_balance()
        if my_balance < amount:
            print(f"[{self.name}] Cannot create tx: insufficient funds ({my_balance} < {amount})")
            return
        
        tx = Transaction(self.name, receivers, amount)
        await self.broadcast_transaction(tx)


    
    # ! must broadcast the result too
    async def mine_block(self):
        """
        Mine a block -> Suggest -> Vote -> Commit
        """
        print(f"\n[{self.name}] ⛏️  STARTING MINING (Phase 1: Proof of Work)...")
        self.is_mining = True
        self.suggested_block = None
        self.votes_received = 0

        # Always add coinbase
        reward = 50 
        coinbase = Transaction("COINBASE", {self.name: 1000 if self.name.lower() == 'coinbase' else reward}, 1000 if self.name.lower() == 'coinbase' else reward)
        transactions = [coinbase] + self.pending_transactions.copy()
        
        loop = asyncio.get_running_loop()
        mined_block = await loop.run_in_executor(None, self.blockchain.create_block, transactions)
        
        print(f"[{self.name}] 💎 Mined Block #{mined_block.index}. Starting Phase 2: Voting...")
        
        # Store as our suggested block
        self.suggested_block = mined_block
        self.is_mining = False

        # Phase 2: Ask for Network Validation (Voting)
        if await self.ask_network_validation(mined_block):
            print(f"[{self.name}] 🗳️  Majority Votes Received! Committing block...")
            await self.announce_winner(mined_block)
            # Commit locally too
            self.handle_commit_request(mined_block)
            return mined_block
        else:
            print(f"[{self.name}] ❌ Voting Failed (Another block won?).")
            self.suggested_block = None
            return None

    # --- MINER SIDE ---
    async def ask_network_validation(self, block):
        """Ask all peers to validate this suggested block"""
        print(f"[{self.name}] 📡 Broadcasting validation request for Block #{block.index}...")
        
        # Convert to dict
        block_data = {
            'index': block.index, 'timestamp': block.timestamp,
            'transactions': [tx.__dict__ for tx in block.transactions],
            'previous_hash': block.previous_hash, 'nonce': block.nonce,
            'hash': block.hash, 'merkle_root': block.merkle_root
        }

        # Count self vote
        yes_votes = 1  
        total_peers = len(self.peers) + 1 # +1 for self
        
        async with httpx.AsyncClient() as client:
            for peer in self.peers.values():
                if not peer.is_alive: continue
                try:
                    response = await client.post(f"{peer.url}/validate_block", json=block_data, timeout=2.0)
                    if response.status_code == 200 and response.json().get("vote") == "YES":
                        yes_votes += 1
                        print(f"[{self.name}] 👍 Peer {peer.name} voted YES")
                    else:
                        print(f"[{self.name}] 👎 Peer {peer.name} voted NO")
                except Exception:
                    pass
        
        return yes_votes > (total_peers / 2)

    async def announce_winner(self, block):
        """Broadcast the commit command for the winning block"""
        print(f"[{self.name}] 📢 Announcing WINNER Block #{block.index} to network...")
        block_data = {
            'index': block.index, 'timestamp': block.timestamp,
            'transactions': [tx.__dict__ for tx in block.transactions],
            'previous_hash': block.previous_hash, 'nonce': block.nonce,
            'hash': block.hash, 'merkle_root': block.merkle_root
        }
        
        async with httpx.AsyncClient() as client:
            for peer in self.peers.values():
                if not peer.is_alive: continue
                try:
                    await client.post(f"{peer.url}/commit_block", json=block_data, timeout=2.0)
                except Exception:
                    pass


    # --- PEER SIDE ---
    def handle_validation_request(self, block) -> bool:
        """
        Vote on a suggested block.
        Conflict Resolution: Earliest Timestamp Wins.
        """
        print(f"[{self.name}] 🗳️  Received Validation Request for Block #{block.index}...")
        
        # 1. Basic Continuity Check
        latest = self.blockchain.get_latest_block()
        if block.index != latest.index + 1 or block.previous_hash != latest.hash:
            print(f"[{self.name}] ❌ Invalid Link (Vote NO)")
            return False

        # 2. Conflict Resolution
        if self.suggested_block:
            # We already have a suggestion (either ours or someone else's)
            if self.suggested_block.hash == block.hash:
                print(f"[{self.name}] 👍 Same block as current suggestion (Vote YES)")
                return True
            
            # Compare Timestamps (Smaller = Older = Winner)
            if block.timestamp < self.suggested_block.timestamp:
                print(f"[{self.name}] 🔄 New block is OLDER ({block.timestamp} < {self.suggested_block.timestamp}). Switching support.")
                self.suggested_block = block
                return True
            else:
                print(f"[{self.name}] ✋ New block is NEWER ({block.timestamp} > {self.suggested_block.timestamp}). Rejecting.")
                return False
        
        # 3. No conflict -> Accept
        self.suggested_block = block
        print(f"[{self.name}] 👍 Accepted as first suggestion (Vote YES)")
        return True

    def handle_commit_request(self, block):
        """Finalize the block (Commit Phase)"""
        print(f"[{self.name}] 🔒 Committing Block #{block.index} to chain!")
        
        # Add to chain
        self.blockchain.chain.append(block)
        
        # Clear specific transactions from mempool
        new_mempool = []
        for pending_tx in self.pending_transactions:
            found = False
            for block_tx in block.transactions:
                if (pending_tx.sender == block_tx.sender and 
                    pending_tx.receivers == block_tx.receivers and 
                    pending_tx.amount == block_tx.amount and 
                    abs(pending_tx.timestamp - block_tx.timestamp) < 5):
                    found = True
                    break
            if not found:
                new_mempool.append(pending_tx)
        
        self.pending_transactions = new_mempool
        self.suggested_block = None # Clear suggestion
        print(f"[{self.name}] ✨ Block Added. Mempool Updated.")



    # Old methods deprecated/removed: broadcast_block, receive_block, handle_new_block (old local version)
    # The new flow uses ask_network_validation -> handle_validation_request -> announce_winner -> handle_commit_request
    


    def get_balance(self):
        """Get balance for this node"""
        print(a:=calculate_balance(self.blockchain, self.name)) #! take off the print after the tests
        return a
    

    def display_status(self):
        """Show current node status"""
        print(f"\n{'='*60}")
        print(f"NODE: {self.name}")
        print(f"UUID: {self.uuid}")
        print(f"URL: {self.url}")
        print(f"{'='*60}")
        print(f"Balance: {self.get_balance()} tokens")
        print(f"Blockchain length: {len(self.blockchain.chain)} blocks")
        print(f"Pending transactions: {len(self.pending_transactions)}")
        print(f"Connected peers ({len(self.peers)}):")
        for peer in self.peers.values():
            status = "✓" if peer.is_alive else "✗"
            print(f"  {status} {peer.name} - {peer.url}")
        print(f"{'='*60}")


    def get_chain(self):
        pass

    # ! now the inter-nodes communication
    
    def request_chain_sync(self, from_peer):
        """Ask a peer for their full chain"""
        print(f"[{self.name}] Requesting full chain sync from {from_peer.name}...")
        from_peer.send_full_chain(self)

    def send_full_chain(self, requester):
        """Send entire blockchain to another node"""
        print(f"[{self.name}] Sending full chain ({len(self.blockchain.chain)} blocks) to {requester.name}")
        # Deep copy to avoid reference issues
        import copy
        chain_copy = copy.deepcopy(self.blockchain.chain)
        requester.receive_full_chain(chain_copy)


    def receive_full_chain(self, new_chain):
        print(f"[{self.name}] Received full chain with {len(new_chain)} blocks")
        
        # Try to replace with longer chain
        replaced = self.blockchain.replace_chain(new_chain)
        
        if replaced:
            # Clear mempool of transactions already in the new chain
            new_tx_strings = set()
            for block in new_chain:
                for tx in block.transactions:
                    if tx.sender != "COINBASE":  # don't remove future rewards
                        new_tx_strings.add(tx.to_string())
            
            self.pending_transactions = [
                tx for tx in self.pending_transactions
                if tx.to_string() not in new_tx_strings
            ]
            print(f"[{self.name}] Chain synchronized successfully!")
        else:
            print(f"[{self.name}] Chain sync rejected (not longer or invalid)")


    def add_peer_url(self, url):
        if url not in self.peer_urls and url != f"http://127.0.0.1:{self.port}":
            self.peer_urls.append(url)
            print(f"[{self.name}] Added peer URL: {url}")








# now this is just a test / real use is in main.py
# new one 
# now this is just a test / real use is in main.py
# new one 
if __name__ == "__main__":
    async def main():
        print("\n" + "="*60)
        print("MULTI-NODE BLOCKCHAIN SIMULATION")
        print("="*60)
        
        # Create bootstrap(genesis) node with genesis
        COINBASE = Node('coinbase', port=5000, difficulty=3, is_genesis=True)
        all_nodes = [COINBASE]

        print("\nSetting up network...")
        nodeA = Node("NodeA", port=5001, difficulty=3)
        nodeB = Node("NodeB", port=5002, difficulty=3)
        nodeC = Node("NodeC", port=5003, difficulty=3)

        all_nodes.extend([nodeA, nodeB, nodeC])
        
        # Connect all nodes
        print("\nConnecting nodes...")
        for node1 in all_nodes:
            for node2 in all_nodes:
                if node1 != node2:
                    node1.connect_to_peer(node2)
        
        # New nodes sync from COINBASE (gets genesis with initial 100 to coinbase)
        print("\n" + "="*60)
        print("NEW NODES SYNCING FROM COINBASE...")
        print("="*60)
        # request_chain_sync implementation in node.py needs review for async?
        # It calls peer.send_full_chain -> peer.receive_full_chain. 
        # All local objects, so synchronous calls are fine for simulation.
        COINBASE.request_chain_sync(COINBASE) # wait, syncing from self? 
        # Actually logic says sync from coinbase.
        nodeA.request_chain_sync(COINBASE)
        nodeB.request_chain_sync(COINBASE)
        nodeC.request_chain_sync(COINBASE)
        
        # Initial funds: COINBASE mines a block (gets 50 reward), then sends to NodeA
        print("\n" + "="*60)
        print("INITIAL SETUP: COINBASE mines & sends 100 to NodeA")
        print("="*60)
        await COINBASE.mine_block()  # ASYNC
        await COINBASE.create_and_broadcast_transaction({"NodeA": 100}, 100) # ASYNC
        
        # Let NodeC mine the tx
        await nodeC.mine_block() # ASYNC
        
        # Scenario: NodeA sends 30 to NodeB
        print("\n" + "="*60)
        print("TRANSACTION 1: NodeA → NodeB (30 tokens)")
        print("="*60)
        await nodeA.create_and_broadcast_transaction({"NodeB": 30}, 30) # ASYNC
        
        print("\n--- Mempool Status ---")
        print(f"COINBASE mempool: {len(COINBASE.pending_transactions)} transactions")
        print(f"NodeA mempool: {len(nodeA.pending_transactions)} transactions")
        print(f"NodeB mempool: {len(nodeB.pending_transactions)} transactions")
        print(f"NodeC mempool: {len(nodeC.pending_transactions)} transactions")
        
        # NodeA mines it
        print("\n" + "="*60)
        print("MINING: NodeA mines the block")
        print("="*60)
        await nodeA.mine_block()
        
        await asyncio.sleep(1)
        
        # Another tx: NodeB → NodeC (10)
        print("\n" + "="*60)
        print("TRANSACTION 2: NodeB → NodeC (10 tokens)")
        print("="*60)
        await nodeB.create_and_broadcast_transaction({"NodeC": 10}, 10)
        
        # NodeB mines it
        print("\n" + "="*60)
        print("MINING: NodeB mines the block")
        print("="*60)
        await nodeB.mine_block()
        
        await asyncio.sleep(1)
        
        # Final status
        print("\n" + "="*60)
        print("FINAL NETWORK STATUS")
        print("="*60)
        
        COINBASE.display_status()
        nodeA.display_status()
        nodeB.display_status()
        nodeC.display_status()
        
        # Sync check
        print("\n" + "="*60)
        print("BLOCKCHAIN SYNCHRONIZATION CHECK")
        print("="*60)
        print(f"COINBASE chain length: {len(COINBASE.blockchain.chain)}")
        print(f"NodeA chain length: {len(nodeA.blockchain.chain)}")
        print(f"NodeB chain length: {len(nodeB.blockchain.chain)}")
        print(f"NodeC chain length: {len(nodeC.blockchain.chain)}")
        
        # Full chain from COINBASE
        print("\n" + "="*60)
        print("FULL BLOCKCHAIN (from COINBASE)")
        print("="*60)
        COINBASE.blockchain.display_chain()

    asyncio.run(main())














