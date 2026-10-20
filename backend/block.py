# block.py
import time
import hashlib
from transaction import Transaction

class Block:
    def __init__(self, index: int, transactions: list, previous_hash: str):
        self.index = index
        self.timestamp = time.time()
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = 0

        self.merkle_root = self.calculate_merkle_root()

        self.hash = self.calculate_hash()



    def calculate_merkle_root(self):
        if not self.transactions:
            return hashlib.sha256("empty".encode()).hexdigest()
        
        tx_hashes = [hashlib.sha256(tx.to_string().encode()).hexdigest() 
                    for tx in self.transactions]
        
        while len(tx_hashes) > 1:
            if len(tx_hashes) % 2 != 0:
                tx_hashes.append(tx_hashes[-1])  
            
            tx_hashes = [hashlib.sha256((tx_hashes[i] + tx_hashes[i+1]).encode()).hexdigest() 
                        for i in range(0, len(tx_hashes), 2)]
        
        return tx_hashes[0]



    def calculate_hash(self) -> str:
        # transactions_string = '|'.join([tx.to_string() for tx in self.transactions])
        # block_string = f"{self.index}|{self.timestamp}|{transactions_string}|{self.previous_hash}|{self.nonce}"
        # ? ^ these 2 now are included in the merkele root func
        
        block_string = f"{self.index}|{self.timestamp}|{self.merkle_root}|{self.previous_hash}|{self.nonce}"
        return hashlib.sha256(block_string.encode()).hexdigest()



    def mine_block(self, difficulty: int):
        target = "0" * difficulty
        
        print(f"Mining block {self.index} | Target: {target}...")
        
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()
            
            if self.nonce % 10000 == 0:
                print(f"  → Nonce: {self.nonce:,} | Current hash: {self.hash[:12]}...")
        
        print(f"Block {self.index} mined! Nonce = {self.nonce}")
        print(f"Final hash: {self.hash}\n")



    def __repr__(self) -> str:
        return (f"Block(index={self.index}, timestamp={self.timestamp}, "
                f"transactions={self.transactions}, previous_hash='{self.previous_hash}', merkle_root='{self.merkle_root}'"
                f"nonce={self.nonce}, hash='{self.hash}')")
    




# ! to test
if __name__ == "__main__":
    from transaction import Transaction
    
    tx1 = Transaction("Alice", {"Bob": 5}, 5)
    tx2 = Transaction("Bob", {"Charlie": 3}, 3)
    
    block = Block(index=1, transactions=[tx1, tx2], previous_hash="0000")
    print(block)
    print(f"Block hash: {block.hash}")