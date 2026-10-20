from blockchain import Blockchain

def calculate_balance(blockchain, address):
    """
    Calculate balance by scanning all transactions in all blocks
    Balance = (received amount) - (sent amount)
    """
    balance = 0
    
    for block in blockchain.chain:
        for transaction in block.transactions:
            if address in transaction.receivers:
                balance += transaction.receivers[address]
            if transaction.sender == address:
                balance -= transaction.amount
    
    return balance



def display_wallet(blockchain, address):
    """
    Show wallet info for an address
    """
    balance = calculate_balance(blockchain, address)
    print(f"\n{'='*50}")
    print(f"Wallet: {address}")
    print(f"Balance: {balance} tokens")
    print(f"{'='*50}")
    
    # Show transaction history
    print("\nTransaction History:")
    for block in blockchain.chain:
        for tx in block.transactions:
            if tx.sender == address:
                print(f"  [SENT] {tx.amount} tokens - Block #{block.index}")
            elif address in tx.receivers:
                received_amount = tx.receivers[address]
                print(f"  [RECEIVED] {received_amount} tokens - Block #{block.index}")


def get_all_wallets(blockchain):
    """
    Get all unique addresses that appear in blockchain
    """
    addresses = set()
    for block in blockchain.chain:
        for tx in block.transactions:
            addresses.add(tx.sender)
            addresses.update(tx.receivers.keys())
    return addresses





def display_all_balances(blockchain):
    """
    Show balances for all wallets
    """
    print("\n" + "="*50)
    print("ALL WALLET BALANCES")
    print("="*50)
    
    addresses = get_all_wallets(blockchain)
    for address in addresses:
        balance = calculate_balance(blockchain, address)
        print(f"{address}: {balance} tokens")






#test  wallet.py
if __name__ == "__main__":
    from blockchain import Blockchain
    from transaction import Transaction
    
    bc = Blockchain(difficulty=3)
    
    # Simulate coinbase: mining rewards
    bc.add_block([Transaction("COINBASE", {"Alice": 50}, 50)])
    bc.add_block([Transaction("COINBASE", {"Bob": 50}, 50)])
    
    # Regular transactions
    bc.add_block([Transaction("Alice", {"Bob": 10}, 10)])
    bc.add_block([Transaction("Bob", {"Charlie": 5}, 5)])
    
    # Check balances
    display_all_balances(bc)
    display_wallet(bc, "Alice")
    display_wallet(bc, "Bob")