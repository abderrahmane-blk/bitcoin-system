# blockchain.py
import time
import hashlib
from block import Block
from transaction import Transaction

class Blockchain:
    def __init__(self , difficulty: int = 4 , genesis=False):
        self.chain = []
        self.difficulty = difficulty
        if genesis:
            self.create_genesis_block()
        

    def create_genesis_block(self):
        coinbase = Transaction("COINBASE", {"coinbase": 100}, 100)  # Initial supply to coinbase node
        genesis = Block(index=0, transactions=[coinbase], previous_hash="0")
        genesis.mine_block(self.difficulty)   
        self.chain.append(genesis)

    def get_latest_block(self):
        return self.chain[-1]

    def contains_transaction(self, transaction) -> bool:
        """Check if a transaction already exists in the blockchain"""
        # We can implement a more robust check based on hash or signature if available
        # For now, we check the content combination
        tx_string = transaction.to_string()
        
        for block in self.chain:
            for tx in block.transactions:
                if tx.to_string() == tx_string:
                    return True
        return False

    def create_block(self, transactions):
        """Mine and return a new block WITHOUT adding it to the chain yet"""
        latest = self.get_latest_block()
        new_block = Block(
            index=latest.index + 1,
            transactions=transactions,
            previous_hash=latest.hash
        )
        new_block.mine_block(self.difficulty)
        return new_block

    def add_block(self, transactions):
        """Legacy helper: Create and add block immediately"""
        new_block = self.create_block(transactions)
        self.chain.append(new_block)
        return new_block



    def replace_chain(self, new_chain):
        """
        Replace local chain with a longer valid chain (consensus rule)
        """

        if len(new_chain) > len(self.chain) and self.is_chain_valid():  # ← fixed name
            self.chain = new_chain
            # Optional: sync difficulty if blocks ever store it (currently they don't)
            # self.difficulty = new_chain[-1].difficulty if hasattr(new_chain[-1], 'difficulty') else self.difficulty
            print(f"  → Chain replaced with longer valid chain (length: {len(new_chain)})")
            return True
        return False


    def is_chain_valid(self) -> bool:
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]

            # 1. Check if the stored hash is still correct
            if current.hash != current.calculate_hash():
                return False

            # 2. Check if the previous_hash link is correct
            if current.previous_hash != previous.hash:
                return False
            
            if current.hash[:self.difficulty] != "0" * self.difficulty:
                return False

            # todo : 3. (Optional for now) Merkle root validation could be added later

        return True




    def display_chain(self):
        print("Blockchain")
        print("=" * 60)
        for i, block in enumerate(self.chain):
            print(f"Block #{i}")
            print(block)
            print("-" * 60)


if __name__ == "__main__":
    from transaction import Transaction

    bc = Blockchain()

    tx1 = Transaction("Alice", {"Bob": 10}, 10)
    tx2 = Transaction("Bob", {"Alice": 5}, 5)
    bc.add_block([tx1,tx2])

    tx2 = Transaction("Bob", {"Charlie": 5}, 5)
    tx3 = Transaction("Charlie", {"Alice": 2}, 2)
    bc.add_block([tx2, tx3])

    bc.display_chain()
    print(f"\nChain valid? {bc.is_chain_valid()}")