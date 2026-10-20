# blockchain.py
import time
import hashlib
from block import Block

class Blockchain:
    def __init__(self):
        self.chain = []
        self.create_genesis_block()

    def create_genesis_block(self):
        genesis = Block(index=0, transactions=[], previous_hash="0")
        self.chain.append(genesis)

    def get_latest_block(self):
        return self.chain[-1]

    def add_block(self, transactions):
        latest = self.get_latest_block()
        new_block = Block(
            index=latest.index + 1,
            transactions=transactions,
            previous_hash=latest.hash
        )
        self.chain.append(new_block)



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

            # 3. (Optional for now) Merkle root validation could be added later
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

    tx1 = Transaction("Alice", "Bob", 10)
    tx2 = Transaction("Bob","Alice" , 5)
    bc.add_block([tx1,tx2])

    tx2 = Transaction("Bob", "Charlie", 5)
    tx3 = Transaction("Charlie", "Alice", 2)
    bc.add_block([tx2, tx3])

    bc.display_chain()
    print(f"\nChain valid? {bc.is_chain_valid()}")