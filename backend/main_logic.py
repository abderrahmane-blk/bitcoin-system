from blockchain import Blockchain
from transaction import Transaction
from wallet import calculate_balance, display_wallet, display_all_balances

# ! this file is to be deleted later
def main():
    print("="*60)
    print("=========BLOCKCHAIN PROJECT======")
    print("="*60)
    

    # Initialize blockchain 
    print("\n1. Creating blockchain...")
    bc = Blockchain(difficulty=3)  # use just 3 for fast calc
    

    # Give Node A initial tokens (coinbase)
    print("\n2. Giving Node A initial 12 tokens (coinbase)...")
    bc.add_block([Transaction("COINBASE", "NodeA", 12)])
    
    print("\nInitial balances:")
    display_all_balances(bc)
    


    # Task 1: Create transaction
    print("\n" + "="*60)
    print("TASK 1: Create Transaction (A → B, 4 tokens)")
    print("="*60)
    tx1 = Transaction("NodeA", "NodeB", 4)
    print(f"Transaction created: {tx1}")
    print(f"Transaction dict: {tx1.to_dict()}")
    


    # Task 2: Send transaction (add to blockchain)
    print("\n" + "="*60)
    print("TASK 2: Send Transaction & Update Balances")
    print("="*60)
    print("Adding transaction to new block and mining...")
    bc.add_block([tx1])
    
    print("\nBalances after transaction:")
    display_wallet(bc, "NodeA")
    display_wallet(bc, "NodeB")
    


    # Task 3: Create block (already done in add_block)
    print("\n" + "="*60)
    print("TASK 3: Block Created")
    print("="*60)
    latest = bc.get_latest_block()
    print(f"Block #{latest.index} created")
    print(f"Transactions in block= {len(latest.transactions)}")
    


    # Task 4: Send block (simulated by add_block)
    print("\n\n\n" + "="*60)
    print("TASK 4: Block Prepared & Sent")
    print("="*60)
    print(f"Merkle Root: {latest.merkle_root}")
    print(f"Previous Hash: {latest.previous_hash}")
    


    # Task 5: Hash block & display blockchain
    print("\n\n\n" + "="*60)
    print("TASK 5: Block Hash & Full Blockchain")
    print("="*60)
    print(f"Block Hash: {latest.hash}")
    print(f"\nFull Blockchain ({len(bc.chain)} blocks):")
    bc.display_chain()
    


    
    # Verify chain integrity
    print("\n" + "="*60)
    print(f"Blockchain Valid? {bc.is_chain_valid()}")
    print("="*60)

if __name__ == "__main__":
    main()